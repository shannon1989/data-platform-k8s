## local access:

curl http://localhost:8083/subjects
curl http://localhost:8083/subjects/blockchain.blocks-key/versions/latest

## API Access:
curl http://schema-registry.kafka.svc:8081/subjects
curl http://schema-registry.kafka.svc:8081/subjects/<subject>/versions/latest

## Python Access:
```Python
from confluent_kafka.schema_registry import SchemaRegistryClient

client = SchemaRegistryClient({'url': 'http://schema-registry.kafka.svc:8081'})
schema = client.get_latest_version("my-subject")
print(schema.schema.schema_str)
```

Schema Registry Evolution rules:
> Compatibility: BACKWARD or FULL
1. Only add fields; do not remove fields.
2. New fields must have a default value.
3. Never change the semantics (meaning) of existing fields.


## Naming convention
blockchain.<chain>.<entity>.<stage>.<producer>

🔹 Raw（Ingestion only）
blockchain.bsc.blocks.raw.ingestion
blockchain.bsc.transactions.raw.ingestion
blockchain.bsc.logs.raw.ingestion

🔹 Refined（Flink）
blockchain.bsc.blocks.cleaned.flink
blockchain.bsc.transactions.cleaned.flink
blockchain.bsc.logs.cleaned.flink

blockchain.bsc.logs.enriched.flink
blockchain.bsc.logs.aggregated.flink

🔹 State / Internal topic
blockchain.bsc.ingestion._state
blockchain.bsc.flink._state

```json
{
    "checkpoint": 77736439,
    "current_range": {
        "end": 77736439,
        "start": 77736439
    },
    "run_id": "b2323d94-4021-48a2-a41e-744c460c5c2d"
}
```