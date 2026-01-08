from dagster import asset, AssetExecutionContext, MetadataValue
import time
import json

from eth_backfill_job import (
    resolve_block_range_by_date,
    load_last_block_from_kafka,
    get_block,
    to_json_safe,
    producer,
    TOPIC_BLOCK,
    STATE_TOPIC,
    STATE_KEY,
    BATCH_SIZE,
)

@asset(
    name="eth_block_backfill",
    compute_kind="ethereum",
    config_schema={
        "start_date": str,
        "end_date": str,
    },
)

def eth_block_backfill(context: AssetExecutionContext):
    # ✅ from Dagster config
    start_date = context.op_config["start_date"]
    end_date = context.op_config["end_date"]

    context.log.info(
        f"Backfill by date: {start_date} → {end_date}"
    )

    start_block, end_block = resolve_block_range_by_date(
        start_date=start_date,
        end_date=end_date,
    )

    producer.init_transactions()
    in_transaction = False
    
    kafka_last = load_last_block_from_kafka()
    start = start_block if kafka_last is None else max(start_block, kafka_last + 1)
    end = end_block

    total = end - start + 1
    processed = 0
    start_ts = time.time()

    current = start
    while current <= end:
        batch_end = min(current + BATCH_SIZE - 1, end)

        try:
            producer.begin_transaction()
            in_transaction = True
            for bn in range(current, batch_end + 1):
                block = get_block(bn)
                block_dict = to_json_safe(dict(block))
                block_dict.pop("transactions", None)

                producer.produce(
                    TOPIC_BLOCK,
                    key=str(bn),
                    value=json.dumps(block_dict),
                )

            producer.produce(
                STATE_TOPIC,
                key=STATE_KEY,
                value=json.dumps({"last_block": batch_end}),
            )

            producer.commit_transaction()

            processed += (batch_end - current + 1)
            progress = processed / total

            # ✅ Dagster native progress reporting
            context.report_asset_progress(progress)

            context.log_event(
                context.asset_materialization(
                    metadata={
                        "current_block": batch_end,
                        "processed_blocks": processed,
                        "total_blocks": total,
                        "progress": MetadataValue.float(progress),
                    }
                )
            )

            current = batch_end + 1

        except Exception as e:
            if in_transaction:
                try:
                    producer.abort_transaction()
                except Exception as abort_err:
                    context.log.warning(f"Abort batch {current}: {e}")
            raise
            time.sleep(3)

    context.log.info("🎉 Backfill finished")