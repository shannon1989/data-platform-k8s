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

## Data modeling

bsc_blocks (only blocks without full transactions)
bsc_transactions (only full transactions)
bsc_logs (only logs)


1️⃣ `blocks` —— 时间轴 & 全局参照系
- block_number
- block_timestamp
- miner / proposer
- baseFee / gasLimit（EIP-1559 链）
- parentHash → reorg 判断

📌 作用：
- 所有事实表的时间维度
- checkpoint / exactly-once
- 链级统计（TPS、gas）

❌ 不承载业务事件


2️⃣ `transactions` —— 交易“意图层”

- from / to
- value（原生币转账）
- input data（函数调用）
- gas / gasPrice / nonce

📌 作用：

- EOA → EOA 转账
- 谁调用了谁（call graph 起点）
- 方法级分析（function selector）

❗️注意：
- 绝大多数“业务事实”不在这里


3️⃣ `logs` —— 事实真相层（最重要）

- ERC20 Transfer
- DEX Swap / Mint / Burn
- NFT Mint / Transfer
- 借贷、清算、质押、治理

📌 这是唯一可靠的“业务事实源”

- 只要合约 emit，你就一定能看到


| 场景           | blocks | tx | logs | 是否覆盖 |
| ------------ | ------ | -- | ---- | ---- |
| BNB 转账       | ❌      | ✅  | ❌    | ✅    |
| ERC20 转账     | ❌      | ❌  | ✅    | ✅    |
| 合约调用         | ❌      | ✅  | ⚠️   | ✅    |
| DEX Swap     | ❌      | ❌  | ✅    | ✅    |
| LP Mint/Burn | ❌      | ❌  | ✅    | ✅    |
| NFT 转移       | ❌      | ❌  | ✅    | ✅    |
| Internal Tx  | ❌      | ❌  | ❌    | ❌    |
| 没有 emit 的逻辑  | ❌      | ⚠️ | ❌    | ❌    |

get_balance
- logs + tx 计算


Reorg:

removed = true

if removed:
    delta_amount = -original_delta
📌 balance 是 可逆的


Kafka
 → Avro decode
 → column 处理
 → order / select
 → Iceberg writer
 → S3A / MinIO IO
 → Iceberg commit

| 阶段                       | 特点                  |
| ------------------------ | ------------------- |
| Kafka read               | 还行                  |
| Avro decode              | CPU 密集              |
| DataFrame transformation | 中等                  |
| Iceberg write            | **重 IO + metadata** |
| MinIO S3A                | 网络 + fsync          |
| Iceberg commit           | driver + metadata   |


Kafka → Spark → ClickHouse ≈ 1–2s
👉 Spark micro-batch + ClickHouse batch insert = 天作之合

| 需求               | 结论          |
| ---------------- | ----------- |
| 100ms 级 SLA      | ❌ Spark 不合适 |
| 实时告警 / CEP       | ❌ Spark 不合适 |
| 秒级 BI / 看板       | ✅ Spark 很合适 |
| 大吞吐写入            | ✅ Spark 很合适 |
| 复杂 SQL transform | ✅ Spark 很合适 |

```TXT
Kafka
 ├─ Spark → Iceberg      （事实层 / 回放） - processTime = 60 seconds
 └─ Spark → ClickHouse   （秒级 OLAP）     - processTime = 1 seconds
```

| 名词            | 行业实际含义        |
| ------------- | ------------- |
| Real-time     | <100ms        |
| Streaming     | <1s           |
| Near realtime | 几十秒 ~ 几分钟 |
| Batch         | ≥ 5–10 分钟     |

```TXT
Spark DataFrame
   ↓
Arrow Columnar Batch（列式内存）
   ↓（零拷贝 / 极少拷贝）
pandas.DataFrame
```