import os
import time
import json
import requests
from confluent_kafka import Producer, Consumer, TopicPartition
from web3 import Web3
from hexbytes import HexBytes
from web3.datastructures import AttributeDict
from datetime import datetime, timedelta, timezone
from typing import Tuple
o resolve block number by time")


# -----------------------------
# Resolver for Dagster config, support passing parameters from Dagster
# -----------------------------
def resolve_block_range_by_date(
    start_date: str,
    end_date: str,
):
    return get_block_range_by_date(
        start_date=start_date,
        end_date=end_date,
    )

# -----------------------------
# Environment Variables
# -----------------------------
ETH_RPC_URL = os.getenv("ETH_RPC_URL")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka-kafka-brokers.kafka.svc.cluster.local:9092")

TOPIC_BLOCK = os.getenv("TOPIC_BLOCK", "eth-blocks")
STATE_TOPIC = os.getenv("STATE_TOPIC", "eth-ingestion-state")
STATE_KEY = os.getenv("STATE_KEY", "eth-mainnet")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))

START_BLOCK = os.getenv("START_BLOCK")
END_BLOCK = os.getenv("END_BLOCK")

START_DATE = os.getenv("START_DATE")
END_DATE = os.getenv("END_DATE")



def resolve_block_range():
    """
    Priority:
      BLOCK > DATE
    """
    if START_BLOCK and END_BLOCK:
        start = int(START_BLOCK)
        end = int(END_BLOCK)
        print(f"Backfill by block range [{start}, {end}]", flush=True)
        return start, end

    if START_DATE and END_DATE:
        return get_block_range_by_date(
            start_date=START_DATE,
            end_date=END_DATE,
        )

    raise RuntimeError(
        "Must provide either "
        "(START_BLOCK & END_BLOCK) "
        "or (START_DATE & END_DATE)"
    )



# -----------------------------
# Resolver for Dagster config, support passing parameters from Dagster
# -----------------------------
def run_eth_backfill(
    transactional_id: str | None = None,
):
    if transactional_id is None:
        transactional_id = os.getenv(
            "TRANSACTIONAL_ID",
            "eth-backfill-job-1"
        )

    # -----------------------------
    # Kafka Producer (Exactly-once)
    # -----------------------------
    producer = Producer({
        "bootstrap.servers": KAFKA_BROKER,
        "acks": "all",
        "enable.idempotence": True,
        "transactional.id": transactional_id,
    })

# -----------------------------
# Web3
# -----------------------------
w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))
if not w3.is_connected():
    raise RuntimeError(f"Cannot connect to Ethereum RPC at {ETH_RPC_URL}")



# -----------------------------
# Fetch block
# -----------------------------
def get_block(bn):
    return w3.eth.get_block(bn, full_transactions=False)

# -----------------------------
# Backfill main logic
# -----------------------------
def backfill():
    START_BLOCK, END_BLOCK = resolve_block_range()
    if END_BLOCK is None:
        raise RuntimeError("END_BLOCK must be set")

    producer.init_transactions()
    in_transaction = False
    
    kafka_last = load_last_block_from_kafka()
    start = int(START_BLOCK) if START_BLOCK else (kafka_last + 1 if kafka_last else 0)
    end = int(END_BLOCK)

    print(f"Backfill blocks [{start}, {end}]", flush=True)

    current = start
    while current <= end:
        batch_end = min(current + BATCH_SIZE - 1, end)

        try:
            producer.begin_transaction()
            in_transaction = True

            for bn in range(current, batch_end + 1):
                block = get_block(bn)
                block_dict = to_json_safe(dict(block))
                block_dict.pop("transactions", None)

                producer.produce(
                    TOPIC_BLOCK,
                    key=str(bn),
                    value=json.dumps(block_dict)
                )

            producer.produce(
                STATE_TOPIC,
                key=STATE_KEY,
                value=json.dumps({"last_block": batch_end})
            )

            producer.commit_transaction()

            print(f"✅ backfilled {current} → {batch_end}", flush=True)
            current = batch_end + 1

        except Exception as e:
            
            if in_transaction:
                try:
                    producer.abort_transaction()
                except Exception as abort_err:
                    context.log.warning(
                        f"Abort transaction failed: {abort_err}"
                    )
            raise
            
            print(f"🔥 abort batch {current}: {e}", flush=True)
            producer.abort_transaction()
            time.sleep(3)

    print("🎉 Backfill finished", flush=True)

# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    backfill()
