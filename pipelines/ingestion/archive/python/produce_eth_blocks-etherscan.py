def fetch_and_push():
    last_block = resolve_start_block(
        job_name=JOB_NAME,
        web3_router=web3_router,
        kafka_broker=KAFKA_BROKER,
        state_topic=STATE_TOPIC,
        schema_registry_url=SCHEMA_REGISTRY_URL,
    )

    log.info(
        "job_start",
        extra={
            "event": "job_start",
            "chain": CHAIN,
            "job": JOB_NAME,
            "start_block": last_block + 1,
        },
    )

    while True:
        try:
            latest_block = web3_router.call(lambda w3: w3.eth.block_number)
            if last_block >= latest_block:
                time.sleep(POLL_INTERVAL)
                continue

            batch_end = min(last_block + BATCH_SIZE, latest_block)

            batch_tx_total = 0
            block_count = 0

            for bn in range(last_block + 1, batch_end + 1):
                block_logs = fetch_block_logs(web3_router, bn)
                if block_logs is None:
                    raise RuntimeError(f"block logs {bn} fetch failed")

                block_logs_safe = to_json_safe(block_logs)

                if isinstance(block_logs_safe, dict):
                    transactions = block_logs_safe.get(
                        "transactions", [block_logs_safe]
                    )
                elif isinstance(block_logs_safe, list):
                    transactions = block_logs_safe
                else:
                    raise RuntimeError(
                        f"Unexpected block_logs type: {type(block_logs_safe)}"
                    )

                total_tx = len(transactions)
                batch_tx_total += total_tx
                block_count += 1

                for start_idx in range(0, total_tx, BATCH_TX_SIZE):
                    batch_tx = transactions[start_idx:start_idx + BATCH_TX_SIZE]

                    for idx, tx in enumerate(batch_tx, start=start_idx):
                        tx_record = {
                            "block_height": bn,
                            "job_name": JOB_NAME,
                            "run_id": RUN_ID,
                            "inserted_at": current_utctime(),
                            "raw": json.dumps(tx),
                            "tx_index": idx,
                        }

                if bn % 100 == 0:
                    log.info(
                        "block_processed",
                        extra={
                            "event": "block_processed",
                            "chain": CHAIN,
                            "job": JOB_NAME,
                            "block": bn,
                            "tx": total_tx,
                        },
                    )