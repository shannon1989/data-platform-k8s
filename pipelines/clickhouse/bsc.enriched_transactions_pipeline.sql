--1.create engine table
CREATE TABLE bsc.kafka_consumer_transactions
(
    -- Avro value（完整反序列化）
    -- ========= 业务字段 =========
    block_height    Int64,
    job_name        String,
    run_id          String,
    raw             String
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'redpanda.kafka.svc:9092',
    kafka_topic_list  = 'blockchain.bsc.ingestion.transactions.raw',
    kafka_group_name  = 'ch_bsc_transactions_consumer',
    kafka_format      = 'AvroConfluent',
    format_avro_schema_registry_url  = 'http://redpanda.kafka.svc:8081',
    kafka_num_consumers = 1;


--2. create target table: bsc.enriched_transactions
CREATE OR REPLACE TABLE bsc.enriched_transactions
(
    -- ========= identity =========
    id String,
    tx_hash String,
    block_number UInt64,
    tx_index UInt64,

    -- ========= address =========
    from_address String,
    to_address String,

    -- ========= value & gas =========
    value_wei UInt256,
    gas_limit UInt64,
    gas_price UInt64,
    max_fee_per_gas UInt64,
    max_priority_fee_per_gas UInt64,

    -- ========= type =========
    tx_type String,
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
    chain_id UInt32,

    -- ========= kafka =========
    kafka_key          String,
    kafka_partition    Int32,
    kafka_offset       Int64,
    kafka_timestamp    DateTime64(3),
    kafka_date         Date
)
ENGINE = MergeTree
PARTITION BY intDiv(block_number, 1000000)
ORDER BY (block_number, tx_index)
SETTINGS index_granularity = 8192;


--3. create pipeline materialized view
CREATE MATERIALIZED VIEW bsc.mv_raw_to_enriched_transactions
TO bsc.enriched_transactions
AS
--enriched_transaction
SELECT
    'enriched_transaction_' || JSONExtractString(raw, 'hash') || '_' || reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'transactionIndex'), '^0x', '')))) as id,
    -- identity
    JSONExtractString(raw, 'hash')                     AS tx_hash,
    block_height AS block_number,
    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'transactionIndex'), '^0x', '')))) AS tx_index,

    -- address
    lower(JSONExtractString(raw, 'from'))              AS from_address,
    lower(JSONExtractString(raw, 'to'))                AS to_address,

    -- value & gas
    reinterpretAsUInt256(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'value'), '^0x', ''))))        				AS value_wei,
    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'gas'), '^0x', ''))))           				AS gas_limit,
    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'gasPrice'), '^0x', ''))))				AS gas_price,
    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'maxFeePerGas'), '^0x', ''))))			AS max_fee_per_gas,
	reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'maxPriorityFeePerGas'), '^0x', ''))))	AS max_priority_fee_per_gas,

    -- type
    JSONExtractString(raw, 'type')                     AS tx_type,

    multiIf(
        to_address IS NULL, 'contract_creation',
        raw = '0x', 'transfer',
        'contract_call'
    ) AS tx_kind,

    multiIf(
        tx_type = '0x2', 'eip1559',
        tx_type = '0x1', 'access_list',
        'legacy'
    ) AS fee_model,

    -- input
    JSONExtractString(raw, 'input')                             AS input_data,
    if(input_data != '0x', substring(input_data, 1, 10), NULL)  AS method_id,
    length(input_data)                                          AS input_length,
    (length(input_data) - 2) / 64                               AS input_words,
    lower(hex(SHA256(input_data)))                              AS input_hash,
    input_data != '0x'                                          AS has_input,
    input_data != '0x'                                          AS is_contract_call,
    ifNull (method_id IN ('0x5c60da1b', '0x3659cfe6'), 0)       AS is_proxy_like,
    -- chain
    reinterpretAsUInt32(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'chainId'), '^0x', '')))) AS chain_id,

    -- kafka
    _key as kafka_key,
    _partition AS kafka_partition,
    _offset    AS kafka_offset,
    _timestamp AS kafka_timestamp,
    toDate(_timestamp) AS kafka_datea
FROM bsc.kafka_consumer_transactions;