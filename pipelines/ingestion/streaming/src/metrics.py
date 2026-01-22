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
    ["chain", "job"],
)
CHAIN_LATEST_BLOCK = Gauge(
    "chain_latest_block",
    "Safe latest block number on chain",
    ["chain", "job"],
)
CHAIN_LATEST_BLOCK_RAW = Gauge(
    "chain_latest_block_raw",
    "Raw latest block number on chain",
    ["chain", "job", "provider"],
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


# -----------------------------
# Kafka
# -----------------------------
KAFKA_TX_FAILURE = Counter(
                "kafka_transaction_failed_total",
                "Kafka transaction failures",
                ["chain", "job"],
            )

COMMIT_INTERVAL = Histogram(
    "commit_interval_sec",
    "Time between successful commits",
    ["chain", "job"],
    buckets=(1, 2, 3, 5, 8, 13, 21, 34, 55, 89),
)

COMMIT_INTERVAL_LATEST = Gauge(
    "commit_interval_sec_latest",
    "Latest commit interval",
    ["chain", "job"],
)

# -----------------------------
# RPC
# -----------------------------
RPC_SUBMITTED = Counter(
    "rpc_submitted_total",
    "Total RPC requests submitted"
)

RPC_STARTED = Counter(
    "rpc_started_total",
    "Total RPC requests started"
)

RPC_COMPLETED = Counter(
    "rpc_completed_total",
    "Total RPC requests completed successfully",
    ["provider", "key"]
)

# Counter（高基数 OK）
RPC_FAILED = Counter(
    "rpc_failed_total",
    "Total RPC requests failed",
    ["provider", "key"]
)

RPC_QUEUE_SIZE = Gauge(
    "rpc_queue_size",
    "Current RPC queue size"
)

RPC_INFLIGHT = Gauge(
    "rpc_inflight",
    "Current inflight RPC count"
)

# Histogram（低基数）
RPC_LATENCY = Histogram(
    "rpc_latency_seconds",
    "RPC call latency",
    ["provider"],
    buckets=(50, 100, 200, 500, 1000, 2000, 5000)
)

RPC_QUEUE_WAIT = Histogram(
    "rpc_queue_wait_seconds",
    "RPC queue wait time",
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5),
)