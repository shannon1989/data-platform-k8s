import os
import json
import uuid
import time
import asyncio
from confluent_kafka.serialization import SerializationContext, MessageField
from prometheus_client import start_http_server
from confluent_kafka import KafkaException
from src.metrics import *
from src.logging import log
from src.rpc_provider import Web3AsyncRouter, AsyncRpcClient, AsyncRpcScheduler, RpcPool, RpcErrorResult, RpcTaskMeta
from src.state import load_last_state
from src.kafka_utils import init_producer, get_serializers, delivery_report
from src.web3_utils import current_utctime, to_json_safe
# from src.commit_timer import CommitTimer
# from src.batch_executor import BatchContext, ParallelBatchExecutor
from src.safe_latest import SafeLatestBlockProvider

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
else:
    JOB_NAME = f"{CHAIN}_realtime_{current_utctime()}"  # 每次唯一，从最新block开始

# -----------------------------
# RPC Config
# -----------------------------
RPC_CONFIG_PATH = "/etc/ingestion/rpc_providers.json"
RPC_MAX_TIMEOUT = int(os.getenv("RPC_MAX_TIMEOUT", "10"))
RPC_MAX_SUBMIT = int(os.getenv("RPC_MAX_SUBMIT", "15")) # how many blocks for every commit to Kafka
RPC_MAX_INFLIGHT = int(os.getenv("RPC_MAX_INFLIGHT", "10"))  # 并发数量

# -----------------------------
# Loing fetching Config
# -----------------------------
RANGE_SIZE = int(os.getenv("RANGE_SIZE", "5")) # how many blocks of range to fetch for logs
BATCH_TX_SIZE = int(os.getenv("BATCH_TX_SIZE", "5"))  # Max 10 logs transaction per batch within a single block
SLIDING_SIZE = int(os.getenv("SLIDING_SIZE", "30"))

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


# Block Range 任务
from dataclasses import dataclass

@dataclass
class BlockRangeTask:
    range_id: int
    start_block: int
    end_block: int
    
# Range 执行结果（RPC → Kafka 的单位）
@dataclass
class RangeResult:
    range_id: int
    start_block: int
    end_block: int
    logs: list
    
    
    
# Range Planner（顺序是从这里开始的）
def plan_block_ranges(start_block: int, end_block: int, range_size: int):
    range_id = 0
    b = start_block

    while b <= end_block:
        yield BlockRangeTask(
            range_id=range_id,
            start_block=b,
            end_block=min(b + range_size - 1, end_block),
        )
        b += range_size
        range_id += 1
        

# OrderedResultBuffer（保证顺序提交）- ingestion 的灵魂组件
class OrderedResultBuffer:
    def __init__(self):
        self._buffer = {}
        self._next_range_id = 0

    def add(self, result: RangeResult):
        self._buffer[result.range_id] = result

    def pop_ready(self):
        ready = []
        while self._next_range_id in self._buffer:
            ready.append(self._buffer.pop(self._next_range_id))
            self._next_range_id += 1
        return ready
      
      
producer = init_producer(TRANSACTIONAL_ID, KAFKA_BROKER)

async def fetch_range_logs(
    start_block: int,
    end_block: int,
    range_size: int,
):
    # -----------------------------
    # RPC infra
    # -----------------------------
    client = AsyncRpcClient(timeout=RPC_MAX_TIMEOUT)
    router = Web3AsyncRouter(rpc_pool, client)

    scheduler = AsyncRpcScheduler(
        router=router,
        max_workers=1,                   # dispatcher 数
        max_inflight=RPC_MAX_INFLIGHT,    # 真正并发 RPC
        max_queue=RPC_MAX_INFLIGHT * 5,
    )

    # -----------------------------
    # Result ordering
    # -----------------------------
    ordered_buffer = OrderedResultBuffer()
    
    # -----------------------------
    # 1️⃣ submit 所有 block ranges
    # -----------------------------
    tasks = []

    for task in plan_block_ranges(start_block, end_block, range_size):
        params = [{
            "fromBlock": hex(task.start_block),
            "toBlock": hex(task.end_block),
            # address / topics
        }]

        tasks.append(
            asyncio.create_task(
                scheduler.submit(
                    "eth_getLogs",
                    params,
                    meta={
                        "range_id": task.range_id,
                        "start_block": task.start_block,
                        "end_block": task.end_block,
                    },
                )
            )
        )

    # ⚠️ gather 保证返回顺序 = submit 顺序
    results = await asyncio.gather(*tasks)

    # -----------------------------
    # 2️⃣ 处理 RPC 结果（乱序 → 有序）
    # -----------------------------
    for r in results:
        if isinstance(r, RpcErrorResult):
            log.error(
                "rpc_range_failed",
                extra={
                    "range_id": r.meta.extra.get("range_id"),
                    "provider": r.rpc,
                    "key": r.key_env,
                    "error": type(r.error).__name__,
                },
            )
            raise RuntimeError("range rpc failed")  # 生产可换成 retry/split

        logs, rpc, key_env, trace, wid, meta = r

        range_result = RangeResult(
            range_id=meta.extra["range_id"],
            start_block=meta.extra["start_block"],
            end_block=meta.extra["end_block"],
            logs=logs or [],   # 🔥 空块是成功
        )

        ordered_buffer.add(range_result)

        # -----------------------------
        # 3️⃣ 尝试顺序写 Kafka
        # -----------------------------
        ready_ranges = ordered_buffer.pop_ready()

        for rr in ready_ranges:
            producer.begin_transaction()
            
            batch_tx_total = 0
            block_count = 0

            range_logs = rr.logs
            
            if range_logs is None:
                raise RuntimeError(
                    f"range logs {start_block}-{end_block} fetch failed"
                )

            range_logs_safe = to_json_safe(range_logs)

            if not isinstance(range_logs_safe, list):
                raise RuntimeError(
                    f"Unexpected range_logs type: {type(range_logs_safe)}"
                )

            # -----------------------------------
            # 按 blockNumber 分组
            # -----------------------------------
            logs_by_block = {}
            
            for log_item in range_logs_safe:
                bn = log_item.get("blockNumber")
                if bn is None:
                    continue

                if isinstance(bn, str):
                    bn = int(bn, 16)

                logs_by_block.setdefault(bn, []).append(log_item)

            # -----------------------------------
            # 逐 block 处理
            # -----------------------------------
            for bn, transactions in logs_by_block.items():
                total_tx = len(transactions)
                batch_tx_total += total_tx
                block_count += 1

                for start_idx in range(0, total_tx, BATCH_TX_SIZE):
                    batch_tx = transactions[
                        start_idx : start_idx + BATCH_TX_SIZE
                    ]

                    for idx, tx in enumerate(batch_tx, start=start_idx):
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
                            on_delivery=delivery_report,
                        )

                    producer.poll(0)
            
            # -----------------------------
            # Commit state
            # -----------------------------
            state_record = {
                "job_name": JOB_NAME,
                "run_id": RUN_ID,
                "range": {"start": meta.extra["start_block"], "end": meta.extra["end_block"]},
                "checkpoint": meta.extra["end_block"],
                "status": "running",
                "inserted_at": current_utctime(),
            }
            # for log_item in rr.logs:
            #     producer.send(
            #         topic=LOG_TOPIC,
            #         key=str(rr.range_id).encode(),
            #         value=serialize_log(log_item),
            #     )

            # 🔥 range 成功 → 推进 checkpoint
            # commit_coordinator.commit(rr.end_block)

            producer.produce(
                STATE_TOPIC,
                key=JOB_NAME,
                value=state_value_serializer(
                    state_record,
                    SerializationContext(STATE_TOPIC, MessageField.VALUE),
                ),
                on_delivery=delivery_report,
            )
            producer.poll(0)
            
            producer.commit_transaction()

            log.info(
                "range_committed",
                extra={
                    "range_id": meta.extra["range_id"],
                    "start": meta.extra["start_block"],
                    "end": meta.extra["end_block"],
                    "rpc": rpc,
                    "key_env": key_env,
                    "log_count": len(rr.logs),
                },
            )

    # -----------------------------
    # 4️⃣ graceful shutdown
    # -----------------------------
    await scheduler.close()
    

if __name__ == "__main__":
    last_block = 76776621
    start_block = last_block + 1
    end_block = start_block + RPC_MAX_INFLIGHT * 5 - 1
    range_size = 5
    asyncio.run(fetch_range_logs(start_block, end_block, range_size))