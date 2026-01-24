import os
import json
import uuid
import time
import asyncio
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
from confluent_kafka.serialization import SerializationContext, MessageField
from prometheus_client import start_http_server
# from confluent_kafka import KafkaException
from src.metrics import *
from src.logging import log
from src.rpc_provider import Web3AsyncRouter, AsyncRpcClient, AsyncRpcScheduler, RpcPool, RpcErrorResult, RpcTaskMeta
from src.state import load_last_state
from src.kafka_utils import init_producer, get_serializers
from src.web3_utils import current_utctime

from src import (
    RangeStatus,
    RangeRegistry,
    RangePlanner,
    OrderedResultBuffer,
    LatestBlockTracker,
)


# -----------------------------
# Environment Variables
# -----------------------------
RUN_ID = os.getenv("RUN_ID", str(uuid.uuid4()))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1")) # can be decimals
CHAIN = os.getenv("CHAIN", "bsc").lower() # bsc, eth, base ... from blockchain-rpc-config.yaml
RESUME_FROM_LAST = os.getenv("RESUME_FROM_LAST", "True").lower() in ("1", "true", "yes")

# -----------------------------
# Job Name & Kafka IDs
# -----------------------------
if RESUME_FROM_LAST:
    JOB_NAME = f"{CHAIN}_backfill_resume"        # 固定名，Kafka checkpoint 能被复用
    JOB_MODE = "resume"
else:
    JOB_NAME = f"{CHAIN}_realtime_{current_utctime()}"  # 每次唯一，从最新block开始
    JOB_MODE = "realtime"

# -----------------------------
# RPC Config
# -----------------------------
RPC_CONFIG_PATH = "/etc/ingestion/rpc_providers.json"
RPC_MAX_TIMEOUT = int(os.getenv("RPC_MAX_TIMEOUT", "10"))
RPC_MAX_INFLIGHT = int(os.getenv("RPC_MAX_INFLIGHT", "10"))
MAX_INFLIGHT_RANGE = int(os.getenv("MAX_INFLIGHT_RANGE", "20"))
# -----------------------------
# Log fetching Config
# -----------------------------
RANGE_SIZE = int(os.getenv("RANGE_SIZE", "5")) # how many blocks of range to fetch for logs
BATCH_TX_SIZE = int(os.getenv("BATCH_TX_SIZE", "5"))  # Max 10 logs transaction per batch within a single block

# -----------------------------
# Kafka Config
# -----------------------------
TRANSACTIONAL_ID = f"blockchain.ingestion.{CHAIN}.{current_utctime()}" # TRANSACTIONAL_ID每次不一样，EOS由Compact State Topic实现
KAFKA_BROKER = "redpanda.kafka.svc:9092"
SCHEMA_REGISTRY_URL = "http://redpanda.kafka.svc:8081"
BLOCKS_TOPIC = f"blockchain.logs.{CHAIN}"
STATE_TOPIC = f"blockchain.state.{CHAIN}"

# -----------------------------
# RPC Initilization
# -----------------------------
rpc_configs = json.load(open(RPC_CONFIG_PATH))
rpc_pool = RpcPool.from_config(rpc_configs, CHAIN)

# -----------------------------
# Kafka Producer initialization
# -----------------------------
blocks_value_serializer, state_value_serializer = get_serializers(SCHEMA_REGISTRY_URL, BLOCKS_TOPIC, STATE_TOPIC)


# Range Status
class RangeStatus(str, Enum):
    PLANNED = "PLANNED"
    INFLIGHT = "INFLIGHT"
    RETRYING = "RETRYING"
    DONE = "DONE"
    FAILED = "FAILED"

# Range 数据面/执行结果（RPC → Kafka 的单位）
@dataclass
class RangeResult:
    range_id: int
    start_block: int
    end_block: int
    logs: list
    rpc: str
    key_env: str
    task_id: int

# 控制面 / 状态机, 不存logs
@dataclass
class RangeRecord:
    range_id: int
    start_block: int
    end_block: int

    status: RangeStatus = RangeStatus.PLANNED
    retry: int = 0
    max_retry: int = 3

    last_error: str | None = None
    last_task_id: int | None = None

    created_ts: float = field(default_factory=time.time)
    updated_ts: float = field(default_factory=time.time)

    def touch(self):
        self.updated_ts = time.time()


class RangeRegistry:
    """
    Single source of truth for range lifecycle.
    """

    def __init__(self):
        self._ranges: dict[int, RangeRecord] = {}

    # -------------------------
    # register
    # -------------------------
    def register(self, range_id: int, start_block: int, end_block: int) -> RangeRecord:
        if range_id in self._ranges:
            raise RuntimeError(f"range {range_id} already registered")

        r = RangeRecord(
            range_id=range_id,
            start_block=start_block,
            end_block=end_block,
        )
        self._ranges[range_id] = r
        return r

    # -------------------------
    # lookup
    # -------------------------
    def get(self, range_id: int) -> RangeRecord:
        try:
            return self._ranges[range_id]
        except KeyError:
            raise KeyError(f"range {range_id} not found")

    # -------------------------
    # state transitions
    # -------------------------
    def mark_inflight(self, range_id: int, task_id: int):
        r = self.get(range_id)
        r.status = RangeStatus.INFLIGHT
        r.last_task_id = task_id
        r.touch()

    def mark_done(self, range_id: int):
        r = self.get(range_id)
        r.status = RangeStatus.DONE
        r.touch()
        self._ranges.pop(range_id, None)

    def mark_failed(self, range_id: int, error: str):
        r = self.get(range_id)
        r.status = RangeStatus.FAILED
        r.last_error = error
        r.touch()
        self._ranges.pop(range_id, None)

    # -------------------------
    # retry logic
    # -------------------------
    def mark_retry(self, range_id: int, error: str) -> bool:
        """
        Returns True if retry allowed, False if exhausted.
        """
        r = self.get(range_id)

        r.retry += 1
        r.last_error = error
        r.touch()

        if r.retry > r.max_retry:
            r.status = RangeStatus.FAILED
            return False

        r.status = RangeStatus.RETRYING
        return True

    # -------------------------
    # helpers
    # -------------------------
    def inflight_count(self) -> int:
        return sum(1 for r in self._ranges.values() if r.status == RangeStatus.INFLIGHT)

    def active_ranges(self) -> list[RangeRecord]:
        return [
            r for r in self._ranges.values()
            if r.status not in (RangeStatus.DONE, RangeStatus.FAILED)
        ]


# Range Planner（顺序是从这里开始的）
@dataclass
class BlockRange:
    range_id: int
    start_block: int
    end_block: int


class RangePlanner:
    """
    只负责：在 latest_block 允许的情况下，持续生成新的 block ranges
    """
    def __init__(self, start_block: int, range_size: int):
        self._next_block = start_block
        self._range_size = range_size
        self._next_range_id = 0

    def next_range(self, latest_block: int) -> Optional[BlockRange]:
        """
        返回下一个可提交的 BlockRange
        如果当前链高度还不够，返回 None
        """
        if self._next_block > latest_block:
            return None

        start = self._next_block
        end = min(
            start + self._range_size - 1,
            latest_block,
        )

        r = BlockRange(
            range_id=self._next_range_id,
            start_block=start,
            end_block=end,
        )

        # 👉 推进游标
        self._next_block = end + 1
        self._next_range_id += 1

        return r


# OrderedResultBuffer（保证顺序提交）- ingestion 的灵魂组件
class OrderedResultBuffer:
    def __init__(self):
        self._buffer = {}
        self._next_range_id = 0

    def add(self, result: RangeRecord):
        self._buffer[result.range_id] = result

    def pop_ready(self):
        ready = []
        while self._next_range_id in self._buffer:
            ready.append(self._buffer.pop(self._next_range_id))
            self._next_range_id += 1
        return ready


class LatestBlockTracker:
    def __init__(self, router, refresh_interval=2.0):
        self.router = router
        self.refresh_interval = refresh_interval
        self._latest: int | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._stopped = False

    def get_cached(self) -> int | None:
        """
        永不 await RPC, 只读缓存
        """
        return self._latest

    async def _refresh_loop(self):
        while not self._stopped:
            try:
                latest = await self.router.get_latest_block()
                async with self._lock:
                    self._latest = latest
            except Exception as e:
                log.warning(
                    "⚠️ latest_block_refresh_failed",
                    extra={"error": str(e)},
                )
            await asyncio.sleep(self.refresh_interval)

    def start(self):
        if not self._task:
            self._task = asyncio.create_task(self._refresh_loop())

    async def stop(self):
        self._stopped = True
        if self._task:
            await self._task



async def submit_range(scheduler, registry, r):
    task = asyncio.create_task(
        scheduler.submit(
            "eth_getLogs",
            [{
                "fromBlock": hex(r.start_block),
                "toBlock": hex(r.end_block),
                # Optional: "topics": [...], "address" : [...]
            }],
            meta={
                "range_id": r.range_id,
                "start_block": r.start_block,
                "end_block": r.end_block,
                "retry": r.retry,
            },
        )
    )

    registry.mark_inflight(r.range_id, task_id=id(task))
    return task



async def stream_ingest_logs(
    *,
    start_block: int,
    range_size: int,
    rpc_pool,
    producer,
    max_inflight_ranges: int = 20,
):
    # -----------------------------
    # RPC infra
    # -----------------------------
    client = AsyncRpcClient(timeout=RPC_MAX_TIMEOUT)
    router = Web3AsyncRouter(rpc_pool, client)

    scheduler = AsyncRpcScheduler(
        router=router,
        max_workers=1,
        max_inflight=RPC_MAX_INFLIGHT,
        max_queue=RPC_MAX_INFLIGHT * 3,
    )

    # -----------------------------
    # Control plane
    # -----------------------------
    planner = RangePlanner(start_block, range_size)
    registry = RangeRegistry()
    
    # -----------------------------
    # Ordering
    # -----------------------------
    ordered_buffer = OrderedResultBuffer()

    # -----------------------------
    # Inflight window
    # -----------------------------
    inflight: set[asyncio.Task] = set()

    # -----------------------------
    # 预填满滑动窗口
    # -----------------------------
    latest_tracker = LatestBlockTracker(router, refresh_interval=2.0)
    latest_tracker.start()

    while True:
        latest_block = latest_tracker.get_cached()
        if latest_block is not None:
            break
        # 启动阶段 or RPC 全挂
        await asyncio.sleep(0.2)


    while len(inflight) < max_inflight_ranges:
        r = planner.next_range(latest_block)
        if not r:
            break
        
        rr = registry.register(
            r.range_id,
            r.start_block,
            r.end_block,
        )
        inflight.add(await submit_range(scheduler, registry, rr))
        
    # -----------------------------
    # 主 streaming loop
    # -----------------------------
    while inflight:
        done, _ = await asyncio.wait(
            inflight,
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in done:
            inflight.remove(task)
            result = await task
            
            # -----------------------------
            #  RPC error processing
            # -----------------------------
            if isinstance(result, RpcErrorResult):
                # 失败 → 标记 RangeRecord 并重试
                meta = result.meta
                range_id = meta.extra["range_id"]
                
                retry_ok = registry.mark_retry(
                    range_id,
                    error=str(result.error),
                )

                log.warning(
                    "❌rpc_range_failed",
                    extra={
                        "range_id": range_id,
                        "retry": registry.get(range_id).retry,
                        "rpc": result.rpc or "UNKNOWN",
                        "error": str(result.error),
                    },
                )
                # 重新提交该 range（换 RPC）
                if retry_ok:
                    r = registry.get(range_id)
                    inflight.add(await submit_range(scheduler, registry, r))
                else:
                    registry.mark_failed(range_id, str(result.error))

                continue # 跳过下面成功处理逻辑

                
            # ----------成功 RPC，解包, 顺序消费 ----------  
            logs, rpc, key_env, trace, wid, meta = result

            rr = RangeResult(
                range_id=meta.extra["range_id"],
                start_block=meta.extra["start_block"],
                end_block=meta.extra["end_block"],
                logs=logs or [],
                rpc=rpc,
                key_env=key_env,
                task_id=meta.task_id,
            )

            ordered_buffer.add(rr)

            # ---------- 顺序消费 ----------
            ready_ranges = ordered_buffer.pop_ready()

            for rr in ready_ranges:
                # ===== Kafka EOS 写入 =====
                producer.begin_transaction()

                logs_by_block = {}
                for log_item in rr.logs:
                    bn = log_item.get("blockNumber")
                    if bn is None:
                        continue
                    if isinstance(bn, str):
                        bn = int(bn, 16)
                    logs_by_block.setdefault(bn, []).append(log_item)

                for bn, txs in logs_by_block.items():
                    total_tx = len(txs)
                    for idx, tx in enumerate(txs):
                        
                        tx_record = {
                            "block_height": bn,
                            "job_name": JOB_NAME,
                            "run_id": RUN_ID,
                            "inserted_at": current_utctime(),
                            "raw": json.dumps(tx),
                            "tx_index": idx,
                        }
                        
                        producer.produce(
                            topic=BLOCKS_TOPIC,
                            key=f"{bn}-{idx}",
                            value=blocks_value_serializer(
                                tx_record,
                                SerializationContext(
                                    BLOCKS_TOPIC, MessageField.VALUE
                                ),
                            ),
                        )
                    producer.poll(0)


                BLOCK_PROCESSED.labels(chain=CHAIN, job=JOB_MODE).inc()
                TX_PROCESSED.labels(chain=CHAIN, job=JOB_MODE).inc(total_tx)
                TX_PER_BLOCK.labels(chain=CHAIN, job=JOB_MODE).observe(total_tx)
                
                # -----------------------------------------
                # commit checkpoint（range 级）
                # -----------------------------------------
                last_committed_block = rr.end_block
                
                state_record = {
                    "job_name": JOB_NAME,
                    "run_id": f"{RUN_ID}-task-{rr.task_id}-range-{rr.range_id}",
                    "range": {
                        "start": rr.start_block,
                        "end": rr.end_block,
                    },
                    "checkpoint": last_committed_block,
                    "status": "running",
                    "inserted_at": current_utctime(),
                }
                
                producer.produce(
                    STATE_TOPIC,
                    key=JOB_NAME,
                    value=state_value_serializer(
                        state_record,
                        SerializationContext(
                            STATE_TOPIC, MessageField.VALUE
                        ),
                    ),
                )
                producer.poll(0)
                producer.commit_transaction()

                registry.mark_done(rr.range_id)
                
                log.info(
                    "✅ range_committed",
                    extra={
                        "task_id": rr.task_id,
                        "range_id": rr.range_id,
                        "start": rr.start_block,
                        "end": rr.end_block,
                        "rpc": rr.rpc,
                        "key_env": rr.key_env,
                        "log_count": len(rr.logs),
                    },
                )

                latest_block = latest_tracker.get_cached()
                if latest_block is not None:
                    CHECKPOINT_BLOCK.labels(chain=CHAIN, job=JOB_MODE).set(last_committed_block)
                    CHECKPOINT_LAG.labels(chain=CHAIN, job=JOB_MODE).set(max(0, latest_block - last_committed_block))
            
            # -----------------------------------------
            # 下游释放 → 上游补位（严格受 registry 控制）
            # -----------------------------------------
            latest_block = latest_tracker.get_cached()
            
            if latest_block is not None:
                while len(inflight) < max_inflight_ranges:
                    r = planner.next_range(latest_block)
                    if not r:
                        break
                    rr = registry.register(
                        r.range_id,
                        r.start_block,
                        r.end_block,
                    )
                    inflight.add(await submit_range(scheduler, registry, rr))

    # -----------------------------
    # shutdown
    # -----------------------------
    await scheduler.close()
    await latest_tracker.stop()

# Entrypoint
async def main():

    last_state = load_last_state(
        job_name=JOB_NAME,
        kafka_broker=KAFKA_BROKER,
        state_topic=STATE_TOPIC,
        schema_registry_url=SCHEMA_REGISTRY_URL,
    )

    last_block = last_state["checkpoint"]

    log.info(
        "▶️job_start",
        extra={
            "chain": CHAIN,
            "job": JOB_NAME,
            "range_size": RANGE_SIZE,
            "log_size" : BATCH_TX_SIZE,
            "start_block": last_block + 1,
        },
    )

    producer = init_producer(TRANSACTIONAL_ID, KAFKA_BROKER)

    await stream_ingest_logs(start_block=last_block + 1,
        range_size=RANGE_SIZE,
        rpc_pool=rpc_pool,
        producer=producer)


if __name__ == "__main__":
    # Prometheus metrics endpoint
    start_http_server(8000)
    asyncio.run(main())