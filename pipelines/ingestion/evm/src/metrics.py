from prometheus_client import Counter, Gauge, Histogram

# -----------------------------
# Lag metrics
# -----------------------------
CHECKPOINT_LAG = Gauge(
    "ingestion_checkpoint_lag",
    "Safe block lag between chain head and ingestion checkpoint",
    ["chain", "job"],
)
CHECKPOINT_LAG_RAW = Gauge(
    "ingestion_checkpoint_lag_raw",
    "Raw block lag between chain head and ingestion checkpoint",
    ["chain", "job", "rpc"],
)
CHAIN_LATEST_BLOCK = Gauge(
    "chain_latest_block",
    "Safe latest block number on chain",
    ["chain", "job"],
)
CHAIN_LATEST_BLOCK_RAW = Gauge(
    "chain_latest_block_raw",
    "Raw latest block number on chain",
    ["chain", "job", "rpc"],
)
CHECKPOINT_BLOCK = Gauge(
    "ingestion_checkpoint",
    "Last committed block by ingestion job",
    ["chain", "job"],
)

# -----------------------------
# Throughput
# -----------------------------
TX_PROCESSED = Counter(
    "ingestion_tx_total",
    "Total number of transactions processed",
    ["chain", "job"],
)
BLOCK_PROCESSED = Counter(
    "ingestion_block_total",
    "Total number of blocks processed",
    ["chain", "job"],
)

TX_PER_BLOCK = Histogram(
    "ingestion_tx_per_block",
    "Transactions per block",
    ["chain", "job"],
    buckets=(50, 100, 200, 500, 1000, 2000, 5000, 10000),
)

COMMIT_INTERVAL = Histogram(
    "commit_interval_sec",
    "Time between successful commits",
    ["chain", "job"],
    buckets=(1, 2, 3, 5, 8, 13, 21, 34),
)

COMMIT_INTERVAL_LATEST = Gauge(
    "commit_interval_sec_latest",
    "Latest commit interval",
    ["chain", "job"],
)

# | bucket | 意义        |
# | ------ | --------- |
# | ≤1s    | 极快 / 理想   |
# | ≤2s    | 正常下限      |
# | ≤3s    | 正常        |
# | ≤5s    | 稳定(SLA p95) |
# | ≤8s    | 稍慢        |
# | ≤13s   | ⚠️ 明显变慢   |
# | ≤21s   | 🚨 接近不可接受 |
# | ≤34s   | 🔥 严重异常   |


# -----------------------------
# RPC
# -----------------------------
RPC_REQUESTS = Counter(
    "rpc_requests_total",
    "RPC requests by provider",
    ["chain", "rpc"]
)
RPC_ERRORS = Counter(
    "rpc_errors_total",
    "RPC errors by provider",
    ["chain", "rpc"]
)

# -----------------------------
# Kafka
# -----------------------------
KAFKA_TX_FAILURE = Counter(
                "kafka_transaction_failed_total",
                "Kafka transaction failures",
                ["chain", "job"],
            )