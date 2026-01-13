from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from src.logging import log

# -----------------------------
# delivery report for producer callback
# -----------------------------
def delivery_report(err, msg):
    if err:
        log.error(
            "kafka_delivery_failed",
            extra={
                "event": "kafka_delivery_failed",
                "topic": msg.topic(),
                "partition": msg.partition(),
                "error": str(err),
            },
        )

def init_producer(TRANSACTIONAL_ID, KAFKA_BROKER):
    producer = Producer({
        "bootstrap.servers": KAFKA_BROKER,
        "enable.idempotence": True,
        "acks": "all",
        "retries": 3,
        "linger.ms": 5,
        "transactional.id": TRANSACTIONAL_ID
    })
    log.info("🔧 Initializing Kafka transactions...")
    producer.init_transactions()
    return producer

def get_serializers(SCHEMA_REGISTRY_URL, BLOCKS_TOPIC, STATE_TOPIC):
    schema_registry = SchemaRegistryClient({"url": SCHEMA_REGISTRY_URL})
    blocks_value_schema = schema_registry.get_latest_version(f"{BLOCKS_TOPIC}-value").schema.schema_str
    state_value_schema = schema_registry.get_latest_version(f"{STATE_TOPIC}-value").schema.schema_str
    return (
        AvroSerializer(schema_registry, blocks_value_schema),
        AvroSerializer(schema_registry, state_value_schema)
    )
