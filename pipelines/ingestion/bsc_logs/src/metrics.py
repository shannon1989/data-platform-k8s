from prometheus_client import Counter, Gauge, Histogram

# Lag metrics
CHECKPOINT_LAG = Gauge(
    "bsc_ingestion_checkpoint_lag",
    "Block lag between chain head and ingestion checkpoint",
    ["job"],
)
CHAIN_LATEST_BLOCK = Gauge(
    "bsc_chain_latest_block",
    "Latest block number on chain",
    ["job"],
)
CHECKPOINT_BLOCK = Gauge(
    "bsc_ingestion_checkpoint",
    "Last committed block by ingestion job",
    ["job"],
)

# Throughput
TX_PROCESSED = Counter(
    "bsc_ingestion_tx_total",
    "Total number of transactions processed",
    ["job"],
)
BLOCK_PROCESSED = Counter(
    "bsc_ingestion_block_total",
    "Total number of blocks processed",
    ["job"],
)

TX_PER_BLOCK = Histogram(
    "bsc_ingestion_tx_per_block",
    "Transactions per block",
    ["job"],
    buckets=(10, 50, 100, 200, 500, 1000, 2000),
)

# RPC
RPC_REQUESTS = Counter(
    "bsc_rpc_requests_total",
    "RPC requests by provider",
    ["rpc"]
)
RPC_ERRORS = Counter(
    "bsc_rpc_errors_total",
    "RPC errors by provider",
    ["rpc"]
)


KAFKA_TX_FAILURE = Counter(
                "bsc_kafka_transaction_failed_total",
                "Kafka transaction failures",
                ["job"],
            )