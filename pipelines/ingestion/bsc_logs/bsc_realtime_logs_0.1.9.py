# -----------------------------
# import deps
# -----------------------------
import os
import json
import uuid
import time

from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField
from hexbytes import HexBytes
from web3.datastructures import AttributeDict
from prometheus_client import start_http_server

# import sys
# sys.path.append("/home/jovyan/work/ingestion/")
from src.metrics import *
from src.logging import log
from src.rpc_provider import RpcProvider, RpcPool, Web3Router
from src.state import resolve_start_block
from src.kafka_utils import init_producer, get_serializers, delivery_report

# -----------------------------
# create current_utctime
# -----------------------------
from datetime import datetime, timezone
def current_utctime():
    """Return the current UTC time string in ISO-8601 format with millisecond precision"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

# -----------------------------
# RPC Pool
# -----------------------------
RPC_CONFIG_PATH = "/etc/ingestion/rpc_providers.json"

with open(RPC_CONFIG_PATH) as f:
    rpc_configs = json.load(f)

def build_rpc_pool(rpc_configs):
    providers = []

    for cfg in rpc_configs:
        if not cfg.get("enabled", True):
            continue

        try:
            url = cfg["url_template"].format(**os.environ)
        except KeyError as e:
            raise RuntimeError(f"Missing env for RPC {cfg['name']}: {e}")

        providers.append(
            RpcProvider(
                name=cfg["name"],
                url=url,
                weight=cfg.get("weight", 1),
            )
        )

    if not providers:
        raise RuntimeError("No RPC providers configured")

    return RpcPool(providers)

rpc_pool = build_rpc_pool(rpc_configs)
web3_router = Web3Router(rpc_pool)

# -----------------------------
# Environment Variables
# -----------------------------
RUN_ID = os.getenv("RUN_ID", str(uuid.uuid4()))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5")) # how many blocks in each batch
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "1"))
BATCH_TX_SIZE = 5  # Max 10 logs transaction per batch within a single block

# -----------------------------
# Config
# -----------------------------

JOB_NAME = "bsc_realtime" + "_" + current_utctime()
TRANSACTIONAL_ID = f"blockchain.ingestion.bsc.{JOB_NAME}"
KAFKA_BROKER = "redpanda.kafka.svc:9092"
SCHEMA_REGISTRY_URL = "http://redpanda.kafka.svc:8081"
BLOCKS_TOPIC = "blockchain.logs.bsc"
STATE_TOPIC = "blockchain.state.bsc"

# -----------------------------
# JSON safe serialization
# -----------------------------
def to_json_safe(obj):
    if isinstance(obj, HexBytes):
        return obj.hex()
    elif isinstance(obj, AttributeDict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_json_safe(v) for v in obj]
    else:
        return obj

# -----------------------------
# Kafka Producer initialization
# -----------------------------
producer = init_producer(TRANSACTIONAL_ID, KAFKA_BROKER)
blocks_value_serializer, state_value_serializer = get_serializers(SCHEMA_REGISTRY_URL, BLOCKS_TOPIC, STATE_TOPIC)

# -----------------------------
# Web3 initialization with router
# -----------------------------
def fetch_block_logs(block_number):
    return web3_router.call(
        lambda w3: w3.eth.get_logs(
            {
                "fromBlock": block_number,
                "toBlock": block_number,
            }
        )
    )


# -----------------------------
# Main function
# - Kafka State + Exactly-once, batched splitting of logs
# -----------------------------
def fetch_and_push():

    last_block = resolve_start_block(JOB_NAME, web3_router)

    log.info(
        "job_start",
        extra={
            "event": "job_start",
            "job": JOB_NAME,
            "start_block": last_block + 1,
        },
    )

    while True:
        latest_block = web3_router.call(lambda w3: w3.eth.block_number)
        CHAIN_LATEST_BLOCK.labels(job=JOB_NAME).set(latest_block)
        CHECKPOINT_BLOCK.labels(job=JOB_NAME).set(last_block)
        CHECKPOINT_LAG.labels(job=JOB_NAME).set(
            max(0, latest_block - last_block)
        )

        if last_block >= latest_block:
            time.sleep(POLL_INTERVAL)
            continue

        batch_end = min(last_block + BATCH_SIZE, latest_block)

        try:
            producer.begin_transaction()

            batch_tx_total = 0
            block_count = 0

            for bn in range(last_block + 1, batch_end + 1):
                block_logs = fetch_block_logs(bn)
                if block_logs is None:
                    raise RuntimeError(f"block logs {bn} fetch failed")

                block_logs_safe = to_json_safe(block_logs)

                if isinstance(block_logs_safe, dict):
                    transactions = block_logs_safe.get("transactions", [block_logs_safe])
                elif isinstance(block_logs_safe, list):
                    transactions = block_logs_safe
                else:
                    raise RuntimeError(f"Unexpected block_logs type: {type(block_logs_safe)}")

                total_tx = len(transactions)
                batch_tx_total += total_tx
                block_count += 1

                for start_idx in range(0, total_tx, BATCH_TX_SIZE):
                    batch_tx = transactions[start_idx:start_idx + BATCH_TX_SIZE]

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
                                SerializationContext(BLOCKS_TOPIC, MessageField.VALUE),
                            ),
                            on_delivery=delivery_report,
                        )

                    producer.poll(0)

                # ✅ block process
                if bn % 100 == 0: # sampling log
                    log.info(
                        "block_processed",
                        extra={
                            "event": "block_processed",
                            "job": JOB_NAME,
                            "block": bn,
                            "tx": total_tx,
                        },
                    )
                BLOCK_PROCESSED.labels(job=JOB_NAME).inc()
                TX_PROCESSED.labels(job=JOB_NAME).inc(total_tx)
                TX_PER_BLOCK.labels(job=JOB_NAME).observe(total_tx)


            # state
            state_record = {
                "job_name": JOB_NAME,
                "run_id": RUN_ID,
                "range": {"start": last_block + 1, "end": batch_end},
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

            # ✅ batch summary (Grafana)
            log.info(
                "batch_committed",
                extra={
                    "event": "batch_committed",
                    "job": JOB_NAME,
                    "blocks": block_count,
                    "tx": batch_tx_total,
                    "range_start": last_block - block_count + 1,
                    "range_end": last_block,
                },
            )
            CHECKPOINT_BLOCK.labels(job=JOB_NAME).set(last_block)
            CHECKPOINT_LAG.labels(job=JOB_NAME).set(
                max(0, latest_block - last_block)
            )

        except Exception as e:
            log.exception(
                "transaction_failed",
                extra={
                    "event": "transaction_failed",
                    "job": JOB_NAME,
                    "last_block": last_block,
                },
            )

            try:
                producer.abort_transaction()
            except Exception as abort_err:
                log.error("abort_transaction_failed | error=%s", abort_err)

            failed_state = {
                "job_name": JOB_NAME,
                "run_id": RUN_ID,
                "range": {"start": last_block, "end": batch_end},
                "checkpoint": last_block - 1,
                "status": "failed",
                "inserted_at": current_utctime(),
            }

            producer.produce(
                STATE_TOPIC,
                key=JOB_NAME,
                value=state_value_serializer(
                    failed_state,
                    SerializationContext(STATE_TOPIC, MessageField.VALUE),
                ),
            )

            producer.flush()
            raise

        time.sleep(POLL_INTERVAL)

# Entrypoint
if __name__ == "__main__":
    # Prometheus metrics endpoint
    start_http_server(8000)
    fetch_and_push()