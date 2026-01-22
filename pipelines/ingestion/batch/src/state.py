
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.serialization import SerializationContext, MessageField
from typing import Optional, Dict, Any
from src.rpc_provider import Web3Router
from src.logging import log


def load_last_state(
    *,
    job_name: str,
    kafka_broker: str,
    state_topic: str,
    schema_registry_url: str,
) -> Optional[Dict[str, Any]]:
    schema_registry_client = SchemaRegistryClient({
        "url": schema_registry_url,
    })
    deserializer = AvroDeserializer(schema_registry_client)

    consumer = Consumer({
        "bootstrap.servers": kafka_broker,
        "group.id": f"state-reader-{job_name}",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "isolation.level": "read_committed",
    })

    consumer.assign([TopicPartition(state_topic, 0)])
    target_key = job_name.encode("utf-8")

    latest_state = None

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            break
        if msg.error():
            continue
        if msg.key() != target_key:
            continue

        latest_state = deserializer(
            msg.value(),
            SerializationContext(state_topic, MessageField.VALUE),
        )

    consumer.close()
    return latest_state


def resolve_start_block(
    *,
    job_name: str,
    web3_router: Web3Router,
    kafka_broker: str,
    state_topic: str,
    schema_registry_url: str,
) -> int:
    last_state = load_last_state(
        job_name=job_name,
        kafka_broker=kafka_broker,
        state_topic=state_topic,
        schema_registry_url=schema_registry_url,
    )

    latest = web3_router.call(lambda w3: w3.eth.block_number)

    if not last_state:
        log.info("no_previous_state", extra={"job": job_name})
        return latest - 1

    checkpoint = last_state.get("checkpoint")
    if checkpoint is None:
        log.warning(
            "⚠️state_without_checkpoint",
            extra={"job": job_name, "state": last_state},
        )
        return latest - 1

    return checkpoint
