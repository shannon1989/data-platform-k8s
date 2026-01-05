import os
import time
import json
from confluent_kafka import Producer, Consumer, TopicPartition
from web3 import Web3
from hexbytes import HexBytes
from web3.datastructures import AttributeDict

# -----------------------------
# JSON safe serializer
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
# Environment Variables
# -----------------------------
ETH_RPC_URL = os.getenv("ETH_RPC_URL")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka-kafka-brokers.kafka.svc.cluster.local:9092")

TOPIC_BLOCK = os.getenv("TOPIC_BLOCK", "eth-blocks")
STATE_TOPIC = os.getenv("STATE_TOPIC", "eth-ingestion-state")
STATE_KEY = os.getenv("STATE_KEY", "eth-mainnet")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

TRANSACTIONAL_ID = os.getenv(
    "TRANSACTIONAL_ID",
    "eth-block-watcher-1"   # ⚠️ 每个实例唯一
)

# -----------------------------
# Kafka Producer（Exactly-once）
# -----------------------------
producer_conf = {
    "bootstrap.servers": KAFKA_BROKER,
    "acks": "all",
    "enable.idempotence": True,
    "retries": 10,
    "linger.ms": 50,
    "transactional.id": TRANSACTIONAL_ID,
}

producer = Producer(producer_conf)

def delivery_report(err, msg):
    if err:
        print(f"❌ delivery failed topic={msg.topic()} key={msg.key()} err={err}", flush=True)
    else:
        print(f"✅ delivered topic={msg.topic()} key={msg.key()} offset={msg.offset()}", flush=True)

# -----------------------------
# Web3
# -----------------------------
w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))
if not w3.is_connected():
    raise RuntimeError(f"Cannot connect to Ethereum RPC: {ETH_RPC_URL}")

# -----------------------------
# read last_block from Kafka compacted topic
# -----------------------------
def load_last_block_from_kafka():
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": f"state-reader-{STATE_KEY}",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })

    tp = TopicPartition(STATE_TOPIC, 0)
    consumer.assign([tp])

    last_block = None
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            break
        if msg.error():
            continue

        if msg.key() and msg.key().decode() == STATE_KEY:
            data = json.loads(msg.value().decode())
            last_block = data["last_block"]

    consumer.close()
    return last_block

# -----------------------------
# Fetch block
# -----------------------------
def get_block(block_number, max_retries=3):
    for _ in range(max_retries):
        try:
            return w3.eth.get_block(block_number, full_transactions=False)
        except Exception as e:
            print(f"❌ fetch block {block_number} failed: {e}")
            time.sleep(2)
    return None

# -----------------------------
# Main function（Kafka State + Exactly-once）
# -----------------------------
def fetch_and_push():
    print("🔧 Initializing Kafka transactions...")
    producer.init_transactions()

    last_block = load_last_block_from_kafka()
    if last_block is None:
        last_block = w3.eth.block_number - 1

    print(f"▶️ Starting from block {last_block + 1}", flush=True)

    while True:
        latest_block = w3.eth.block_number
        if last_block >= latest_block:
            time.sleep(POLL_INTERVAL)
            continue

        batch_end = min(last_block + BATCH_SIZE, latest_block)

        try:
            # 🔐 Kafka Transaction
            producer.begin_transaction()

            # 1️⃣ produce blocks
            for bn in range(last_block + 1, batch_end + 1):
                block = get_block(bn)
                if block is None:
                    raise RuntimeError(f"block {bn} fetch failed")

                block_dict = to_json_safe(dict(block))
                block_dict.pop("transactions", None)

                producer.produce(
                    TOPIC_BLOCK,
                    key=str(block.number),
                    value=json.dumps(block_dict),
                    callback=delivery_report
                )

            # 2️⃣ produce state (single write)
            state_value = json.dumps({"last_block": batch_end})
            producer.produce(
                STATE_TOPIC,
                key=STATE_KEY,
                value=state_value
            )

            producer.poll(0)

            # commit transaction（blocks + state）
            producer.commit_transaction()

            last_block = batch_end
            print(f"✅ committed blocks up to {last_block}", flush=True)

        except Exception as e:
            print(f"🔥 transaction failed, aborting: {e}", flush=True)
            producer.abort_transaction()
            time.sleep(3)

        time.sleep(POLL_INTERVAL)

# Entrypoint
if __name__ == "__main__":
    fetch_and_push()
