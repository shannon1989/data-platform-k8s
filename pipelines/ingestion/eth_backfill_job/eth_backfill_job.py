import os
import sys
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField
import json
from datetime import datetime, timezone
import uuid
from typing import Optional
from web3 import Web3
from hexbytes import HexBytes
from web3.datastructures import AttributeDict
from dataclasses import dataclass
from src.etherscan import get_block_range_by_date
from src.kafka_state import load_last_state


# -----------------------------
# Environment Variables
# -----------------------------
ETH_INFURA_RPC_URL = os.getenv("ETH_INFURA_RPC_URL", "https://mainnet.infura.io/v3/<YOUR_API_KEY>")
if not ETH_INFURA_RPC_URL or "<YOUR_API_KEY>" in ETH_INFURA_RPC_URL:
    raise RuntimeError("ETH_INFURA_RPC_URL is not configured")

START_BLOCK = os.getenv("START_BLOCK")
END_BLOCK = os.getenv("END_BLOCK")

START_DATE = os.getenv("START_DATE")
END_DATE = os.getenv("END_DATE")

run_id = os.getenv("RUN_ID", str(uuid.uuid4()))

JOB_NAME = os.getenv("JOB_NAME")
if not JOB_NAME:
    raise RuntimeError("JOB_NAME is not configured")


print('================ Environment Variables =================')
print("JOB_NAME: ", JOB_NAME)
print("START_DATE: ", START_DATE)
print("END_DATE: ", END_DATE)
print("run_id: ", run_id)
print('========================================================')

# -----------------------------
# Config
# -----------------------------
JOB_DESC = "eth_backfill"
KAFKA_BROKER = "redpanda.kafka.svc:9092"
SCHEMA_REGISTRY_URL = "http://redpanda.kafka.svc:8081"
BLOCKS_TOPIC = "blockchain.blocks.eth.mainnet"
STATE_TOPIC = "blockchain.ingestion-state.eth.mainnet"
STATE_KEY = "blockchain.ingestion-state.eth.mainnet-key"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))

# -----------------------------
# Schema Registry
# -----------------------------
schema_registry = SchemaRegistryClient({
    "url": SCHEMA_REGISTRY_URL
})

current_utctime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

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
# resolve backfill context: date | block
# -----------------------------
@dataclass(frozen=True)
class BackfillContext:
    start_block: int
    end_block: int

def resolve_backfill_context() -> BackfillContext: # type hint
    """
    Priority:
      BLOCK > DATE

    Returns:
      BackfillContext object
    """
    if START_BLOCK and END_BLOCK:
        start = int(START_BLOCK)
        end = int(END_BLOCK)
        
        return BackfillContext(
            start_block = start,
            end_block = end,
        )

    if START_DATE and END_DATE:
        start_block, end_block = get_block_range_by_date(
            start_date = START_DATE,
            end_date = END_DATE,
        )
        
        date_key = f"{START_DATE}_{END_DATE}".replace("-", "")
        return BackfillContext(
            start_block = start_block,
            end_block = end_block,
        )

    raise RuntimeError(
        "Invalid backfill parameters : "
        "Must provide either ""(START_BLOCK & END_BLOCK) ""or (START_DATE & END_DATE)"
    )
    
ctx = resolve_backfill_context()
transactional_id = f"blockchain.ingestion.eth.mainnet.{JOB_NAME}"

# -----------------------------
# resolve start block height for in-job retry/failure
# -----------------------------
def resolve_start_block() -> Optional[int]:
    state = load_last_state(JOB_NAME)

    # 1️⃣ Completed: exit the job
    if state and state["status"] == "completed":
        print(f"✅ Backfill {JOB_NAME} already completed")
        sys.exit(0)   # 👈 terminalate Python program

    # 2️⃣ resume
    if state:
        last = state["checkpoint"]
        end = state["range"]["end"]

        if last >= end:
            print(f"⚠️ State inconsistent: last >= end, treat as completed")
            sys.exit(0)

        start_block = last + 1
        print(f"🔁 Resume {JOB_NAME} from block {start_block}")
        return start_block

    # 3️⃣ new job
    print(f"🚀 Start new job {JOB_NAME} from block {ctx.start_block}")
    return ctx.start_block


# --- Avro schemas（pull registry）
blocks_value_schema = schema_registry.get_latest_version(
    f"{BLOCKS_TOPIC}-value"
).schema.schema_str

state_value_schema = schema_registry.get_latest_version(
    f"{STATE_TOPIC}-value"
).schema.schema_str

# -----------------------------
# Serializers
# -----------------------------
blocks_value_serializer = AvroSerializer(
    schema_registry,
    blocks_value_schema
)

state_value_serializer = AvroSerializer(
    schema_registry,
    state_value_schema
)

# -----------------------------
# Web3
# -----------------------------
w3 = Web3(Web3.HTTPProvider(ETH_INFURA_RPC_URL))
if not w3.is_connected():
    raise RuntimeError(f"Cannot connect to Ethereum RPC at {ETH_INFURA_RPC_URL}")

# -----------------------------
# Fetch block
# -----------------------------
def get_block(bn):
    return w3.eth.get_block(bn, full_transactions=False)


# -----------------------------
# delivery report for producer callback
# -----------------------------
def delivery_report(err, msg):
    if err is not None:
        print(f"❌ Delivery failed: {err}")
    else:
        print(
            f"✅ Delivered to {msg.topic()} "
            f"[{msg.partition()}] @ {msg.offset()}"
        )

# -----------------------------
# Producer initialization
# -----------------------------
producer = Producer({
    "bootstrap.servers": KAFKA_BROKER,
    "enable.idempotence": True,
    "acks": "all",
    "retries": 3,
    "linger.ms": 5,
    "transactional.id": transactional_id
})

producer.init_transactions()

# -----------------------------
# Backfill main logic
# -----------------------------
def backfill():

    start = resolve_start_block()
    end = ctx.end_block

    current = start
    while current <= end:
        batch_end = min(current + BATCH_SIZE - 1, end)

        try:
            producer.begin_transaction()

            for bn in range(current, batch_end + 1):
                block = get_block(bn)
                block_dict = to_json_safe(dict(block))
                block_dict.pop("transactions", None)

                block_record = {
                    "block_height": bn,
                    "JOB_NAME": JOB_NAME,
                    "run_id": run_id,
                    "inserted_at": current_utctime,
                    "raw": json.dumps(block_dict),
                }

                producer.produce(
                    topic=BLOCKS_TOPIC,
                    key=str(bn),
                    value=blocks_value_serializer(
                        block_record,
                        SerializationContext(BLOCKS_TOPIC, MessageField.VALUE)
                    ),
                    on_delivery=delivery_report,
                )
                
            producer.poll(0)

            # checking if all transaction is done
            is_last_batch = batch_end >= end
            status = "completed" if is_last_batch else "running"
            
            state_record = {
                "JOB_NAME": JOB_NAME,
                "run_id": run_id,
                "range": {
                    "start": start,
                    "end": end
                },
                "checkpoint": batch_end,
                "status": status,
                "inserted_at": current_utctime
            }

            producer.produce(
                STATE_TOPIC,
                key=JOB_NAME,
                value=state_value_serializer(
                    state_record,
                    SerializationContext(STATE_TOPIC, MessageField.VALUE)
                ),
                on_delivery=delivery_report,
            )
            
            producer.poll(0)
            producer.commit_transaction()

            print(f"✅ backfilled {current} → {batch_end} ", flush=True)
            current = batch_end + 1
            
        except Exception as e:
            print(f"🔥 abort batch {current}: {e}", flush=True)

            # abort transaction, rollback blocks
            try:
                producer.abort_transaction()
            except Exception as abort_err:
                print(f"Abort transaction failed: {abort_err}")

            # normal write for failed status
            failed_state = {
                "JOB_NAME": JOB_NAME,
                "run_id": run_id,
                "start_block": start,
                "end_block": end,
                "last_processed_block": current - 1,  # the last success block
                "status": "failed",
                "inserted_at": current_utctime
            }

            producer.produce(
                STATE_TOPIC,
                key=JOB_NAME,
                value=state_value_serializer(
                    failed_state,
                    SerializationContext(STATE_TOPIC, MessageField.VALUE)
                ),
                on_delivery=delivery_report,
            )

            producer.flush()

            raise   # error capture for Dagster / k8s

    print("🎉 Backfill finished", flush=True)
    producer.flush()


# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    backfill()