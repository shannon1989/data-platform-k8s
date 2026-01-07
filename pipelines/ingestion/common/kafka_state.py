import os
import json
from confluent_kafka import Producer, Consumer, TopicPartition

# -----------------------------
# Environment Variables
# -----------------------------
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka-kafka-brokers.kafka.svc.cluster.local:9092")
STATE_TOPIC = os.getenv("STATE_TOPIC", "eth-ingestion-state")
STATE_KEY = os.getenv("STATE_KEY", "eth-mainnet")


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