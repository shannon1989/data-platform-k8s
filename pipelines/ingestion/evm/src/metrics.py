from prometheus_client import Counter, Gauge, Histogram

# -----------------------------
# Lag metrics
# -----------------------------
CHECKPOINT_LAG = Gauge(
    "ingestion_checkpoint_lag",
    "Block lag between chain head and ingestion checkpoint",
    ["chain", "job"],
)
CHAIN_LATEST_BLOCK = Gauge(
    "chain_latest_block",
    "Latest block number on chain",
    ["chain", "job"],
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
    buckets=(10, 50, 100, 200, 500, 1000, 2000),
)

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