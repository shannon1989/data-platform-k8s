# -----------------------------
# import deps
# -----------------------------
import os
import json
import uuid
import time
from confluent_kafka.serialization import SerializationContext, MessageField
from prometheus_client import start_http_server
from confluent_kafka import KafkaException
from src.metrics import *
from src.logging import log
from src.rpc_provider import RpcPool, Web3Router, RpcTemporarilyUnavailable
from src.state import resolve_start_block
from src.kafka_utils import init_producer, get_serializers, delivery_report
from src.web3_utils import current_utctime
from src.commit_timer import CommitTimer
from src.batch_executor import BatchContext, ParallelBatchExecutor
from src.safe_latest import SafeLatestBlockProvider

# -----------------------------
# Environment Variables
# -----------------------------
RUN_ID = os.getenv("RUN_ID", str(uuid.uuid4()))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "15")) # how many blocks for every commit to Kafka
RANGE_SIZE = int(os.getenv("RANGE_SIZE", "3")) # how many blocks of range to fetch for logs
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5")) # how many worker thread for a batch range
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1")) # can be decimals
BATCH_TX_SIZE = int(os.getenv("BATCH_TX_SIZE", "5"))  # Max 10 logs transaction per batch within a single block
CHAIN = os.getenv("CHAIN", "base").lower() # bsc, eth, base ... from blockchain-rpc-config.yaml

# -----------------------------
# Behavior Control, Job Name & Kafka IDs
# -----------------------------
JOB_MODE = os.getenv("JOB_MODE", "realtime").lower() # backfill or realtime, realtime by default

if JOB_MODE == "backfill":
    JOB_NAME = f"{CHAIN}_{JOB_MODE}"        # 固定名，Kafka checkpoint 能被复用
else:
    JOB_NAME = f"{CHAIN}_{JOB_MODE}_{current_utctime()}"  # 每次唯一，从最新block开始

# -----------------------------
# Config
# -----------------------------
TRANSACTIONAL_ID = f"blockchain.ingestion.{CHAIN}.{JOB_MODE}.{current_utctime()}" # TRANSACTIONAL_ID每次不一样，EOS由Compact State Topic实现
KAFKA_BROKER = "redpanda.kafka.svc:9092"
SCHEMA_REGISTRY_URL = "http://redpanda.kafka.svc:8081"
BLOCKS_TOPIC = f"blockchain.logs.{CHAIN}"
STATE_TOPIC = f"blockchain.state.{CHAIN}"
RPC_CONFIG_PATH = "/etc/ingestion/rpc_providers.json" 

# -----------------------------
# load RPC Pool
# -----------------------------
with open(RPC_CONFIG_PATH) as f:
    rpc_configs = json.load(f)

rpc_pool = RpcPool.from_config(
    rpc_configs=rpc_configs,
    chain=CHAIN,
)

web3_router = Web3Router(
    rpc_pool=rpc_pool,
    chain=CHAIN,
    timeout=10,
    penalize_seconds=15,
)

# -----------------------------
# Kafka Producer initialization
# -----------------------------
blocks_value_serializer, state_value_serializer = get_serializers(SCHEMA_REGISTRY_URL, BLOCKS_TOPIC, STATE_TOPIC)

# -----------------------------
# Kafka State + Exactly-once, batched splitting of logs
# -----------------------------
def fetch_and_push():
    global producer
    commit_timer = CommitTimer()
    
    last_block = resolve_start_block(
        job_name=JOB_NAME,
        web3_router=web3_router,
        kafka_broker=KAFKA_BROKER,
        state_topic=STATE_TOPIC,
        schema_registry_url=SCHEMA_REGISTRY_URL,
    )

    log.info(
        "▶️job_start",
        extra={
            # "event": "job_start",
            "chain": CHAIN,
            "job": JOB_NAME,
            "job_mode" : JOB_MODE,
            "batch_size": BATCH_SIZE,
            "range_size": RANGE_SIZE,
            "log_size" : BATCH_TX_SIZE,
            "max_workers": MAX_WORKERS,
            "start_block": last_block + 1,
        },
    )

    producer = init_producer(TRANSACTIONAL_ID, KAFKA_BROKER)

    while True:
        try:
            # -----------------------------
            # Retrieve validated, monotonic latest block number
            # -----------------------------
            safe_latest_provider = SafeLatestBlockProvider(
                chain=CHAIN,
                job=JOB_NAME,
                max_reorg_tolerance=5,
                max_block_jump=200,
            )

            t0 = time.time()
            raw_latest_block, provider_ctx = web3_router.call_with_provider(lambda w3: w3.eth.block_number)
            commit_timer.mark_rpc(provider_ctx.rpc, time.time() - t0)

            latest_block = safe_latest_provider.update(
                raw_block=raw_latest_block,
                rpc_name=provider_ctx.rpc,
            )
            # current value - no history, no incremental, overriden
            CHECKPOINT_BLOCK.labels(chain=CHAIN, job=JOB_NAME).set(last_block)
        
            if last_block >= latest_block:
                time.sleep(POLL_INTERVAL)
                continue
            
            # -----------------------------
            # # batch_start / batch_end define the immutable boundary of this batch
            # -----------------------------
            batch_start = last_block + 1
            batch_end = min(last_block + BATCH_SIZE, latest_block)

            if batch_end < batch_start:
                log.warning(
                    "⚠️ invalid_batch_range",
                    extra={
                        "batch_start": batch_start,
                        "batch_end": batch_end,
                        "latest_block": latest_block,
                        "last_block": last_block,
                    },
                )
                time.sleep(POLL_INTERVAL)
                continue

            # -----------------------------
            # Kafka Transaction
            # -----------------------------
            producer.begin_transaction()
            
            executor = ParallelBatchExecutor(max_workers=MAX_WORKERS)

            ctx = BatchContext(
                web3_router=web3_router,
                producer=producer,
                commit_timer=commit_timer,
                job_name=JOB_NAME,
                run_id=RUN_ID,
                chain=CHAIN,
                blocks_topic=BLOCKS_TOPIC,
                batch_tx_size=BATCH_TX_SIZE,
                blocks_value_serializer=blocks_value_serializer,
            )

            web3_router.begin_batch()
            try:
                result = executor.execute(
                    ctx,
                    batch_start=batch_start,
                    batch_end=batch_end,
                    range_size=RANGE_SIZE,
                )

                block_count = result["block_count"]
                batch_tx_total = result["tx_total"]
            finally:
                web3_router.end_batch()
                
            # -----------------------------
            # Commit state
            # -----------------------------
            state_record = {
                "job_name": JOB_NAME,
                "run_id": RUN_ID,
                "range": {"start": batch_start, "end": batch_end},
                "checkpoint": batch_end,
                "status": "running",
                "inserted_at": current_utctime(),
            }

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

            last_block = batch_end

            commit_metrics = commit_timer.commit_cost()
            
            log.info(
                "✅ batch_committed",
                extra={
                    # "event": "batch_committed",
                    # "chain": CHAIN,
                    # "job": JOB_NAME,
                    # 与 state topic 100% 一致
                    "range_start": batch_start,
                    "range_end": batch_end,
                    # 实际处理情况
                    "blocks": block_count,
                    "tx": batch_tx_total,
                    # metrics
                    "commit_interval_sec": commit_metrics["commit_interval_sec"]
                },
            )
            
            CHECKPOINT_LAG.labels(chain=CHAIN, job=JOB_NAME).set(max(0, latest_block - last_block))
            CHECKPOINT_LAG_RAW.labels(chain=CHAIN, job=JOB_NAME).set(max(0, raw_latest_block - last_block))
            
            commit_interval_sec = commit_metrics.get("commit_interval_sec")
            if isinstance(commit_interval_sec, (int, float)) and commit_interval_sec >= 0:
                COMMIT_INTERVAL.labels(chain=CHAIN, job=JOB_NAME).observe(commit_interval_sec) # histogram (time series)
                COMMIT_INTERVAL_LATEST.labels(chain=CHAIN, job=JOB_NAME).set(commit_interval_sec) # stat
                
        # -------------------------------------------------
        # 🟡 1️⃣ RPC 临时不可用（最轻）
        # -------------------------------------------------
        except RpcTemporarilyUnavailable:
            log.warning(
                "⚠️ rpc_temporarily_unavailable",
                extra={
                    # "event": "rpc_temporarily_unavailable",
                    "chain": CHAIN,
                    "job": JOB_NAME,
                    "last_block": last_block,
                },
            )

            # ❗ 不碰 Kafka 事务
            time.sleep(2)
            continue

        # -------------------------------------------------
        # 🔶 2️⃣ Kafka 事务失败（需要 abort + 重建）
        # -------------------------------------------------
        except KafkaException as e:
            log.exception(
                "❌ kafka_transaction_failed",
                extra={
                    # "event": "kafka_transaction_failed",
                    "chain": CHAIN,
                    "job": JOB_NAME,
                    "last_block": last_block,
                },
            )

            KAFKA_TX_FAILURE.labels(chain=CHAIN, job=JOB_NAME).inc()
            
            # best-effort abort
            try:
                producer.abort_transaction()
            except Exception:
                pass
            
            # ❗️销毁 producer
            try:
                producer.flush(5)
            except Exception:
                pass

            producer = None

            # backoff，防止抖动
            time.sleep(3)
            # 重新创建 producer（新的事务上下文）
            producer = init_producer(TRANSACTIONAL_ID, KAFKA_BROKER)
            # ❗️不 raise，继续 while True
            continue

        # -------------------------------------------------
        # 🔴 3️⃣ 真正不可恢复的程序错误
        # -------------------------------------------------
        except Exception as e:
            # -----------------------------
            # 🚨 Runtime failure
            # -----------------------------
            log.exception(
                "🔥 fatal_runtime_error",
                extra={
                    # "event": "fatal_runtime_error",
                    "chain": CHAIN,
                    "job": JOB_NAME,
                    "last_block": last_block,
                    "error_type": type(e).__name__,
                },
            )
            
            # ❗ 这里让 Pod 挂掉是正确的
            raise

        time.sleep(POLL_INTERVAL)


# Entrypoint
if __name__ == "__main__":
    # Prometheus metrics endpoint
    start_http_server(8000)
    fetch_and_push()