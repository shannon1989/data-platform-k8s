CREATE TABLE bsc.normalized_transactions
(
    id String,

    tx_hash String,
    block_number UInt64,
    tx_index UInt64,

    from_address String,
    to_address String,

    value_wei UInt256,
    gas_limit UInt64,
    gas_price UInt64,
    max_fee_per_gas UInt64,
    max_priority_fee_per_gas UInt64,

    tx_type String,

    input_data String,
    chain_id UInt32
)
ENGINE = MergeTree
PARTITION BY intDiv(block_number, 1000000)
ORDER BY (block_number, tx_index)
SETTINGS index_granularity = 8192;


CREATE MATERIALIZED VIEW bsc.mv_transactions_normalized
TO bsc.normalized_transactions
AS
SELECT
    'normalized_transaction_' || JSONExtractString(raw, 'hash') || '_' ||
    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'transactionIndex'), '^0x', '')))) AS id,

    JSONExtractString(raw, 'hash') AS tx_hash,

    block_height AS block_number,

    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'transactionIndex'), '^0x', '')))) AS tx_index,

    lower(JSONExtractString(raw, 'from')) AS from_address,
    lower(JSONExtractString(raw, 'to')) AS to_address,

    reinterpretAsUInt256(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'value'), '^0x', '')))) AS value_wei,

    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'gas'), '^0x', '')))) AS gas_limit,

    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'gasPrice'), '^0x', '')))) AS gas_price,

    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'maxFeePerGas'), '^0x', '')))) AS max_fee_per_gas,

    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'maxPriorityFeePerGas'), '^0x', '')))) AS max_priority_fee_per_gas,

    replaceRegexpOne(JSONExtractString(raw, 'type'), '^0x', '') AS tx_type,

    JSONExtractString(raw, 'input') AS input_data,

    reinterpretAsUInt32(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'chainId'), '^0x', '')))) AS chain_id

FROM bsc.transactions_raw
WHERE JSONExtractString(raw, 'hash') IS NOT NULL;


--initial load

INSERT INTO bsc.normalized_transactions
SELECT
    'normalized_transaction_' || JSONExtractString(raw, 'hash') || '_' ||
    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'transactionIndex'), '^0x', '')))) AS id,

    JSONExtractString(raw, 'hash') AS tx_hash,

    block_height AS block_number,

    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'transactionIndex'), '^0x', '')))) AS tx_index,

    lower(JSONExtractString(raw, 'from')) AS from_address,
    lower(JSONExtractString(raw, 'to')) AS to_address,

    reinterpretAsUInt256(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'value'), '^0x', '')))) AS value_wei,

    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'gas'), '^0x', '')))) AS gas_limit,

    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'gasPrice'), '^0x', '')))) AS gas_price,

    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'maxFeePerGas'), '^0x', '')))) AS max_fee_per_gas,

    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'maxPriorityFeePerGas'), '^0x', '')))) AS max_priority_fee_per_gas,

    replaceRegexpOne(JSONExtractString(raw, 'type'), '^0x', '') AS tx_type,

    JSONExtractString(raw, 'input') AS input_data,

    reinterpretAsUInt32(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'chainId'), '^0x', '')))) AS chain_id

FROM bsc.transactions_raw where block_height < 84944072; --from (select min(block_number) from bsc.normalized_transactions)