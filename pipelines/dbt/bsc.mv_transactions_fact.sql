-- equivalent to spark transform_bronze_to_silver
CREATE MATERIALIZED VIEW bsc.mv_transactions_fact_local
ON CLUSTER analytics -- shard / replica > 1
TO bsc.mainnet_transactions_fact
AS
SELECT
    -- identity
    JSONExtractString(raw, 'hash')                     AS tx_hash,
    block_height,
    reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'blockNumber'), '^0x', '')))) AS block_number,
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
    kafka_partition,
    kafka_offset,
    kafka_timestamp,
    kafka_date
FROM kafka.bsc_transactions_raw
WHERE JSONExtractString(raw, 'hash') IS NOT NULL;