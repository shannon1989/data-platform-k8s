
kubectl create ns airbyte
helm repo add airbyte https://airbytehq.github.io/helm-charts
helm repo update

helm install airbyte airbyte/airbyte \
  -n airbyte \
  -f airbyte-values.yaml


port-forward svc/airbyte-aribyte-server-svc


Kafka Config in Airbyte:
{
  "name": "Kafka",
  "workspaceId": "7459350e-1223-4f37-821e-9edc6311123e",
  "definitionId": "9f760101-60ae-462f-9ee6-b7a9dafd454d",
  "configuration": {
    "acks": "all",
    "compression_type": "snappy",
    "client_dns_lookup": "use_all_dns_ips",
    "enable_idempotence": true,
    "retries": 2147483647,
    "protocol": {
      "security_protocol": "PLAINTEXT"
    },
    "linger_ms": "0",
    "batch_size": 50,
    "max_block_ms": "60000",
    "buffer_memory": "33554432",
    "sync_producer": false,
    "topic_pattern": "airbyte.blockchain",
    "max_request_size": 1048576,
    "bootstrap_servers": "redpanda.kafka.svc:9092",
    "send_buffer_bytes": 131072,
    "request_timeout_ms": 30000,
    "delivery_timeout_ms": 120000,
    "receive_buffer_bytes": 32768,
    "socket_connection_setup_timeout_ms": "10000",
    "max_in_flight_requests_per_connection": 5,
    "socket_connection_setup_timeout_max_ms": "30000"
  }
}