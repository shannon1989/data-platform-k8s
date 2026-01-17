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
from src.rpc_provider import RpcProvider, RpcPool, Web3Router
from src.state import resolve_start_block
from src.kafka_utils import init_producer, get_serializers, delivery_report
from src.web3_utils import fetch_range_logs, to_json_safe, current_utctime
from src.rpc_provider import RpcTemporarilyUnavailable
from src.commit_timer import CommitTimer
# -----------------------------
# Environment Variables
# -----------------------------
RUN_ID = os.getenv("RUN_ID", str(uuid.uuid4()))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10")) # how many blocks for every commit to Kafka
RANGE_SIZE = int(os.getenv("RANGE_SIZE", "5")) # how many blocks of range to fetch for logs
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1")) # can be decimals
BATCH_TX_SIZE = int(os.getenv("BATCH_TX_SIZE", "5"))  # Max 10 logs transaction per batch within a single block
CHAIN = os.getenv("CHAIN", "base").lower() # bsc, eth, base ... from blockchain-rpc-config.yaml

# -----------------------------
# Behavior Control
# -----------------------------
# If True -> resume from last processed block using Kafka state topic
# If False -> start from latest block
RESUME_FROM_LAST = os.getenv("RESUME_FROM_LAST", "True").lower() in ("1", "true", "yes")

# -----------------------------
# Job Name & Kafka IDs
# -----------------------------
if RESUME_FROM_LAST:
    JOB_NAME = f"{CHAIN}_realtime"        # 固定名，Kafka checkpoint 能被复用
else:
    JOB_NAME = f"{CHAIN}_realtime_{current_utctime()}"  # 每次唯一，从最新block开始


TRANSACTIONAL_ID = f"blockchain.ingestion.{CHAIN}.{current_utctime()}" # TRANSACTIONAL_ID每次不一样，EOS由Compact State Topic实现
KAFKA_BROKER = "redpanda.kafka.svc:9092"
SCHEMA_REGISTRY_URL = "http://redpanda.kafka.svc:8081"
BLOCKS_TOPIC = f"blockchain.logs.{CHAIN}"
STATE_TOPIC = f"blockchain.state.{CHAIN}"

# -----------------------------
# load RPC Pool
# -----------------------------
RPC_CONFIG_PATH = "/etc/ingestion/rpc_providers.json"
with open(RPC_CONFIG_PATH) as f:
    rpc_configs = json.load(f)

def build_rpc_url(cfg: dict) -> str:
    """
    Build final RPC URL from provider config.
    """
    base_url = cfg["base_url"]
    key_env = cfg.get("api_key_env")
    # Public RPC
    if not key_env:
        return base_url

    api_key = os.getenv(key_env)
    if not api_key:
        raise RuntimeError(
            f"Missing env var for RPC provider "
            f"{cfg['name']}: {key_env}"
        )
    
    return f"{base_url}/{api_key}"

def build_rpc_pool(rpc_configs: dict, chain: str) -> "RpcPool":
    chain_cfg = rpc_configs.get("chains", {}).get(chain)
    if not chain_cfg:
        raise RuntimeError(f"Chain config not found: {chain}")

    providers = []

    for cfg in chain_cfg.get("providers", []):
        if not cfg.get("enabled", True):
            continue

        url = build_rpc_url(cfg)

        providers.append(
            RpcProvider(
                name=cfg['name'],
                url=url,
                weight=int(cfg.get("weight", 1)),
            )
        )

    if not providers:
        raise RuntimeError(f"No RPC providers enabled for chain: {chain}")

    return RpcPool(providers)

rpc_pool = build_rpc_pool(rpc_configs, CHAIN)
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
# Main function
# - Kafka State + Exactly-once, batched splitting of logs
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
        "job_start",
        extra={
            # "event": "job_start",
            "chain": CHAIN,
            "job": JOB_NAME,
            "start_block": last_block + 1,
        },
    )

    producer = init_producer(TRANSACTIONAL_ID, KAFKA_BROKER)

    while True:
        try:
            # -----------------------------
            # 获取最新区块
            # -----------------------------
            t0 = time.time()
            latest_block, rpc_name = web3_router.call_with_provider(lambda w3: w3.eth.block_number)
            commit_timer.mark_rpc(rpc_name, time.time() - t0)
            
            CHAIN_LATEST_BLOCK.labels(chain=CHAIN, job=JOB_NAME).set(latest_block)
            CHECKPOINT_BLOCK.labels(chain=CHAIN, job=JOB_NAME).set(last_block)
            CHECKPOINT_LAG.labels(chain=CHAIN, job=JOB_NAME).set(max(0, latest_block - last_block))

            if last_block >= latest_block:
                time.sleep(POLL_INTERVAL)
                continue
            
            # -----------------------------
            # # batch_start / batch_end define the immutable boundary of this batch
            # -----------------------------
            batch_start = last_block + 1
            batch_end = min(last_block + BATCH_SIZE, latest_block)

            # -----------------------------
            # Kafka Transaction
            # -----------------------------
            producer.begin_transaction()

            batch_tx_total = 0
            block_count = 0

            for range_start in range(
                batch_start,
                batch_end + 1,
                RANGE_SIZE,
            ):
                range_end = min(range_start + RANGE_SIZE - 1, batch_end)

                t0 = time.time()
                range_logs, rpc_name = fetch_range_logs(
                    web3_router,
                    range_start,
                    range_end,
                    with_provider=True,
                )
                commit_timer.mark_rpc(rpc_name, time.time() - t0)

                if range_logs is None:
                    raise RuntimeError(
                        f"range logs {range_start}-{range_end} fetch failed"
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


                    if bn % 1000 == 0:
                        log.info(
                            "block_processed",
                            extra={
                                # "event": "block_processed",
                                "chain": CHAIN,
                                "job": JOB_NAME,
                                "block": bn,
                                "tx": total_tx,
                            },
                        )
                        
                    BLOCK_PROCESSED.labels(chain=CHAIN, job=JOB_NAME).inc()
                    TX_PROCESSED.labels(chain=CHAIN, job=JOB_NAME).inc(total_tx)
                    TX_PER_BLOCK.labels(chain=CHAIN, job=JOB_NAME).observe(total_tx)
           
            
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
            )

            producer.poll(0)
            producer.commit_transaction()

            last_block = batch_end

            commit_metrics = commit_timer.commit_cost()
            
            log.info(
                "batch_committed",
                extra={
                    # "event": "batch_committed",
                    "chain": CHAIN,
                    "job": JOB_NAME,
                    
                    # 与 state topic 100% 一致
                    "range_start": batch_start,
                    "range_end": batch_end,

                    # 实际处理情况
                    "blocks": block_count,
                    "tx": batch_tx_total,
                    
                    # metrics
                    "commit_interval_sec": commit_metrics["commit_interval_sec"],
                    "rpc_cost_sec": commit_metrics["rpc_cost_sec"],
                    # "rpc_calls": commit_metrics["rpc_calls"],
                    # "avg_rpc_cost": commit_metrics["avg_rpc_cost"]
                },
            )
            
            CHECKPOINT_BLOCK.labels(chain=CHAIN, job=JOB_NAME).set(last_block)
            CHECKPOINT_LAG.labels(chain=CHAIN, job=JOB_NAME).set(max(0, latest_block - last_block))

        # -------------------------------------------------
        # 🟡 1️⃣ RPC 临时不可用（最轻）
        # -------------------------------------------------
        except RpcTemporarilyUnavailable:
            log.warning(
                "rpc_temporarily_unavailable",
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
                "kafka_transaction_failed",
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
                "fatal_runtime_error",
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