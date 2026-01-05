# Exactly-Once ingestion and store the state with compacted topic
  - pipeline containerization
  - Block-based ingestion
  - Time-based backfill
  - Kafka Exactly-Once
  - Compact topic state
  - Streaming / Batch jobs
  - Airflow scheduler supported

eth_backfill_job.py
-> show progress of block data ingestion (eg. 6%)
-> gost proxy for stablizied RPC
-> Linux server date accuracy issue.

# build docker image inside k8s docker

```bash
eval $(minikube docker-env)
```

```bash
docker build -t eth-ingestion:latest .
```

```YAML
apiVersion: batch/v1
kind: Job
metadata:
  name: eth-block-ingestion-test
  namespace: airflow
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: eth-ingestion
        image: eth-ingestion:latest
        env:
        - name: ETH_RPC_URL
          valueFrom:
            secretKeyRef:
              name: eth-secrets
              key: rpc_url
```

```YAML
kubectl create secret generic eth-secrets \
  -n airflow \
  --from-literal=rpc_url=https://mainnet.infura.io/v3/YOUR_API_KEY

kubectl create secret generic etherscan \
  -n airflow \
  --from-literal=api_key=YOUR_API_KEY
```


### Create topic
```YAML
apiVersion: batch/v1
kind: Job
metadata:
  name: create-eth-state-topic
  namespace: kafka
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: kafka-client
        image: quay.io/strimzi/kafka:0.49.1-kafka-4.1.1
        # kafka-topics.sh path is different in Strimzi images
        command:
          - sh
          - -c
          - |
            /opt/kafka/bin/kafka-topics.sh --create \
              --topic eth-ingestion-state \
              --bootstrap-server kafka-kafka-bootstrap.kafka.svc.cluster.local:9092 \
              --partitions 1 \
              --replication-factor 1 \
              --config cleanup.policy=compact || true

```

### Emoji rules

- ▶️  job start
- ⏸️  idle / waiting
- 📦  batch start
- ✅  success / commit
- ⚠️  retryable warning
- ❌  single operation failed
- 🔥  transaction aborted / fatal


## Dagster 

1. build image
eval $(minikube docker-env)
docker build -t eth-dagster-user-code:0.1.0 .
