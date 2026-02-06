CREATE TABLE bsc.transactions_fact_local
--ON CLUSTER analytics
(
    -- ========= identity =========
    tx_hash            FixedString(66),
    block_height       Int64,
    block_number       Int64,
    tx_index           Int32,

    -- ========= address =========
    from_address       FixedString(42),
    to_address         Nullable(FixedString(42)),

    -- ========= value & gas =========
    value_wei          UInt256,
    gas_limit          UInt64,
    gas_price          Nullable(UInt64),
    max_fee_per_gas    Nullable(UInt64),
    max_priority_fee_per_gas Nullable(UInt64),

    -- ========= type =========
    tx_type            String,
    tx_kind            LowCardinality(String),
    fee_model          LowCardinality(String),

    -- ========= input =========
    input_data         String,
    method_id          Nullable(FixedString(10)),
    input_length       UInt32,
    input_words        UInt32,
    input_hash         FixedString(64),
    has_input          UInt8,
    is_contract_call   UInt8,
    is_proxy_like      Nullable(UInt8),

    -- ========= chain =========
    chain_id           UInt32,

    -- ========= kafka =========
    kafka_key          String,
    kafka_partition    Int32,
    kafka_offset       Int64,
    kafka_timestamp    DateTime64(3),
    kafka_date         Date
)
ENGINE = MergeTree
PARTITION BY kafka_date
ORDER BY (block_height, tx_index, tx_hash);
