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

BASE_URL = "https://api.etherscan.io/v2/api?chainid=1"

# -----------------------------
# Date → unix timestamp (UTC) [start, end)
# -----------------------------
def date_to_timestamp(date_str: str, end: bool = False) -> int:
    """
    date_str: 'YYYY-MM-DD'
    end=False  -> Current Date 00:00:00 UTC
    end=True   -> Next Day 00:00:00 UTC
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    dt = dt.replace(tzinfo=timezone.utc)

    if end:
        dt = dt + timedelta(days=1)

    return int(dt.timestamp())

# -----------------------------
# Etherscan: timestamp → block number
# -----------------------------
def get_block_no_by_time(
    unix_timestamp: int,
    closest: str,
    max_retries: int = 3,
) -> int:
    """
    closest: 'before' | 'after'
    """
    assert closest in ("before", "after")

    params = {
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": unix_timestamp,
        "closest": closest,
        "apikey": ETHERSCAN_API_KEY,
    }

    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(BASE_URL, params=params, timeout=10)
            res.raise_for_status()

            data = res.json()
            result = data.get("result")

            if result is None:
                raise RuntimeError(f"Empty result: {data}")

            return int(result)

        except Exception as e:
            print(
                f"❌ getblocknobytime failed "
                f"(ts={unix_timestamp}, closest={closest}, attempt={attempt}): {e}",
                flush=True,
            )
            time.sleep(2)

    raise RuntimeError("Failed to resolve block number by time")

# -----------------------------
# utility func：date range → block range
# -----------------------------
def get_block_range_by_date(
    start_date: str,
    end_date: str,
) -> Tuple[int, int]:
    """
    Input:
      start_date: 'YYYY-MM-DD'
      end_date:   'YYYY-MM-DD'

    Apply:
      [start_date 00:00:00,
       end_date+1 00:00:00)
    """

    if start_date > end_date:
        raise ValueError("start_date > end_date")

    start_ts = date_to_timestamp(start_date, end=False)
    end_ts = date_to_timestamp(end_date, end=True)

    start_block = get_block_no_by_time(
        unix_timestamp=start_ts,
        closest="after",
    )

    end_block = get_block_no_by_time(
        unix_timestamp=end_ts,
        closest="before",
    )

    if start_block > end_block:
        raise RuntimeError(
            f"Invalid block range: {start_block} > {end_block}"
        )

    print(
        f"Date range {start_date} ~ {end_date} "
        f"→ blocks [{start_block}, {end_block}]",
        flush=True,
    )

    return start_block, end_block

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

TRANSACTIONAL_ID = os.getenv(
    "TRANSACTIONAL_ID",
    "eth-backfill-job-1"   # unique per Job
)

# -----------------------------
# Kafka Producer (Exactly-once)
# -----------------------------
producer = Producer({
    "bootstrap.servers": KAFKA_BROKER,
    "acks": "all",
    "enable.idempotence": True,
    "transactional.id": TRANSACTIONAL_ID,
})

# -----------------------------
# Web3
# -----------------------------
w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))
if not w3.is_connected():
    raise RuntimeError(f"Cannot connect to Ethereum RPC at {ETH_RPC_URL}")

# -----------------------------
# read last_block from Kafka compact topic
# -----------------------------
def load_last_block_from_kafka():
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": f"state-reader-{STATE_KEY}",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })

    consumer.assign([TopicPartition(STATE_TOPIC, 0)])

    last_block = None
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            break
        if msg.error():
            continue

        if msg.key() and msg.key().decode() == STATE_KEY:
            last_block = json.loads(msg.value())["last_block"]

    consumer.close()
    return last_block

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

    kafka_last = load_last_block_from_kafka()
    start = int(START_BLOCK) if START_BLOCK else (kafka_last + 1 if kafka_last else 0)
    end = int(END_BLOCK)

    print(f"Backfill blocks [{start}, {end}]", flush=True)

    current = start
    while current <= end:
        batch_end = min(current + BATCH_SIZE - 1, end)

        try:
            producer.begin_transaction()

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
            print(f"🔥 abort batch {current}: {e}", flush=True)
            producer.abort_transaction()
            time.sleep(3)

    print("🎉 Backfill finished", flush=True)

# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    backfill()
