import time
import json
from pipelines.ingestion.bsc_realtime_logs.logging import log
from pipelines.ingestion.bsc_realtime_logs.metrics import (
    CHAIN_LATEST_BLOCK,
    CHECKPOINT_BLOCK,
    CHECKPOINT_LAG,
    BLOCK_PROCESSED,
    TX_PROCESSED,
    TX_PER_BLOCK,
)
from pipelines.ingestion.bsc_realtime_logs.time_utils import current_utctime
from pipelines.ingestion.bsc_realtime_logs.state import resolve_start_block
from pipelines.ingestion.bsc_realtime_logs.web3_utils import fetch_block_logs, to_json_safe
from confluent_kafka.serialization import SerializationContext, MessageField

BATCH_TX_SIZE = 5  # Max tx per mini-batch

def fetch_and_push(
    JOB_NAME: str,
    RUN_ID: str,
    web3_router,
    producer,
    blocks_value_serializer,
    state_value_serializer,
    BATCH_SIZE: int,
    POLL_INTERVAL: int,
    BLOCKS_TOPIC="blockchain.logs.bsc",
    STATE_TOPIC="blockchain.state.bsc"
):
    last_block = resolve_start_block(JOB_NAME, web3_router)

    log.info(
        "job_start",
        extra={"event": "job_start", "job": JOB_NAME, "start_block": last_block + 1},
    )

    while True:
        latest_block = web3_router.call(lambda w3: w3.eth.block_number)
        CHAIN_LATEST_BLOCK.labels(job=JOB_NAME).set(latest_block)
        CHECKPOINT_BLOCK.labels(job=JOB_NAME).set(last_block)
        CHECKPOINT_LAG.labels(job=JOB_NAME).set(max(0, latest_block - last_block))

        if last_block >= latest_block:
            time.sleep(POLL_INTERVAL)
            continue

        batch_end = min(last_block + BATCH_SIZE, latest_block)

        try:
            producer.begin_transaction()

            batch_tx_total = 0
            block_count = 0

            for bn in range(last_block + 1, batch_end + 1):
                block_logs = fetch_block_logs(web3_router, bn)
                if block_logs is None:
                    raise RuntimeError(f"block logs {bn} fetch failed")

                block_logs_safe = to_json_safe(block_logs)

                if isinstance(block_logs_safe, dict):
                    transactions = block_logs_safe.get("transactions", [block_logs_safe])
                elif isinstance(block_logs_safe, list):
                    transactions = block_logs_safe
                else:
                    raise RuntimeError(f"Unexpected block_logs type: {type(block_logs_safe)}")

                total_tx = len(transactions)
                batch_tx_total += total_tx
                block_count += 1

                # 分小批次发送
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
                        producer.produce(
                            topic=BLOCKS_TOPIC,
                            key=f"{bn}-{idx}",
                            value=blocks_value_serializer(
                                tx_record,
                                SerializationContext(BLOCKS_TOPIC, MessageField.VALUE),
                            ),
                        )
                    producer.poll(0)

                if bn % 100 == 0:
                    log.info(
                        "block_processed",
                        extra={"event": "block_processed", "job": JOB_NAME, "block": bn, "tx": total_tx},
                    )

                BLOCK_PROCESSED.labels(job=JOB_NAME).inc()
                TX_PROCESSED.labels(job=JOB_NAME).inc(total_tx)
                TX_PER_BLOCK.labels(job=JOB_NAME).observe(total_tx)

            # state record
            state_record = {
                "job_name": JOB_NAME,
                "run_id": RUN_ID,
                "range": {"start": last_block + 1, "end": batch_end},
                "checkpoint": batch_end,
                "status": "running",
                "inserted_at": current_utctime(),
            }
            producer.produce(
                STATE_TOPIC,
                key=JOB_NAME,
                value=state_value_serializer(
                    state_record,
                    SerializationContext(STATE_TOPIC, MessageField.VALUE),
                ),
            )
            producer.poll(0)
            producer.commit_transaction()

            last_block = batch_end

            log.info(
                "batch_committed",
                extra={
                    "event": "batch_committed",
                    "job": JOB_NAME,
                    "blocks": block_count,
                    "tx": batch_tx_total,
                    "range_start": last_block - block_count + 1,
                    "range_end": last_block,
                },
            )

            CHECKPOINT_BLOCK.labels(job=JOB_NAME).set(last_block)
            CHECKPOINT_LAG.labels(job=JOB_NAME).set(max(0, latest_block - last_block))

        except Exception as e:
            log.exception(
                "transaction_failed",
                extra={"event": "transaction_failed", "job": JOB_NAME, "last_block": last_block},
            )
            try:
                producer.abort_transaction()
            except Exception as abort_err:
                log.error("abort_transaction_failed | error=%s", abort_err)

            failed_state = {
                "job_name": JOB_NAME,
                "run_id": RUN_ID,
                "range": {"start": last_block, "end": batch_end},
                "checkpoint": last_block - 1,
                "status": "failed",
                "inserted_at": current_utctime(),
            }
            producer.produce(
                STATE_TOPIC,
                key=JOB_NAME,
                value=state_value_serializer(
                    failed_state,
                    SerializationContext(STATE_TOPIC, MessageField.VALUE),
                ),
            )
            producer.flush()
            raise
