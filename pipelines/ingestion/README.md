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
docker build -t eth-backfill:0.1.4 .

Clash ubuntu server install:
```bash
sudo wget https://github.com/MetaCubeX/mihomo/releases/download/Prerelease-Alpha/mihomo-linux-amd64-v2-alpha-1e1434d.gz
```

Check previous log:
kubectl logs -n airflow bsc-logs-ingestion-b548dcf69-ftxzh --previous

Search logs inside the POD:
```bash
kubectl logs -n airflow deploy/base-logs-ingestion \
  | jq 'select(.level=="WARNING")'
```

开源组件：stakater/reloader
kubectl apply -f https://raw.githubusercontent.com/stakater/Reloader/master/deployments/kubernetes/reloader.yaml

metadata:
  annotations:
    reloader.stakater.com/auto: "true"

ConfigMap 一改 -> Pod 自动重启

spec:
  replicas: 1
  strategy:
    type: Recreate # 强制单实例 + 串行切换 （先 kill 旧 Pod，再建新 Pod）Kafka EOS 安全

Loki安装：
```bash
helm install loki grafana/loki-stack \
  --namespace prometheus \
  --set grafana.enabled=false \
  --set promtail.enabled=true
```