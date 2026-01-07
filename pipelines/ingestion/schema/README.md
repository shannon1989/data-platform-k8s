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