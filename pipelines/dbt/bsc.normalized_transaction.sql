--normalized_transaction
SELECT
    'normalized_transaction_' || JSONExtractString(raw, 'hash') || '_' || reinterpretAsUInt64(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'transactionIndex'), '^0x', '')))) as id,
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
    replaceRegexpOne(JSONExtractString(raw, 'type'), '^0x', '')              AS tx_type,

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
    -- chain
    reinterpretAsUInt32(reverse(unhex(replaceRegexpOne(JSONExtractString(raw, 'chainId'), '^0x', '')))) AS chain_id
FROM bsc.transactions_raw
WHERE JSONExtractString(raw, 'hash') IS NOT NULL;