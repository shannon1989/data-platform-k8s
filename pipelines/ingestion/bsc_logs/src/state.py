
import os
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.serialization import SerializationContext, MessageField
from typing import Optional, Dict, Any

from src.rpc_provider import Web3Router
from src.logging import log

# -----------------------------
# Config
# -----------------------------
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda.kafka.svc:9092")
STATE_TOPIC = os.getenv("STATE_TOPIC", "blockchain.state.bsc.mainnet")

SCHEMA_REGISTRY_URL = "http://redpanda.kafka.svc:8081"

# -----------------------------
# consumer initialization
# -----------------------------
schema_registry_conf = {
    "url": SCHEMA_REGISTRY_URL,
}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

job_state_deserializer = AvroDeserializer(schema_registry_client)


# -----------------------------
# consumer main logic
# -----------------------------
def load_last_state(job_name: str) -> Optional[Dict[str, Any]]:
    latest_state = None # initialize state value
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": f"state-reader-{job_name}",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "isolation.level": "read_committed",
    })

    consumer.assign([TopicPartition(STATE_TOPIC, 0)])

    target_key = job_name.encode("utf-8")

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            break
        if msg.error():
            continue
        if msg.key() != target_key:
            continue

        latest_state = job_state_deserializer(
            msg.value(),
            SerializationContext(STATE_TOPIC, MessageField.VALUE),
        )

    consumer.close()
    return latest_state


def resolve_start_block(job_name: str, web3_router: Web3Router) -> int:
    last_state = load_last_state(job_name)
    latest = web3_router.call(lambda w3: w3.eth.block_number)

    if not last_state:
        log.info("no_previous_state", extra={"job": job_name})
        return latest - 1

    checkpoint = last_state.get("checkpoint")
    if checkpoint is None:
        log.warning("state_without_checkpoint", extra={"job": job_name, "state": last_state})
        return latest - 1

    return checkpoint
