CREATE TABLE bsc.transactions_fact
ON CLUSTER analytics
AS bsc.mainnet_transactions_fact
ENGINE = Distributed(
    analytics,
    bsc,
    mainnet_transactions_fact,
    cityHash64(tx_hash)
);
