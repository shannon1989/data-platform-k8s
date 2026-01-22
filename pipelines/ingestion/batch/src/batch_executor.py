import time
import json
import threading
from dataclasses import dataclass
from confluent_kafka.serialization import SerializationContext, MessageField
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.kafka_utils import delivery_report
from src.web3_utils import fetch_range_logs, to_json_safe, current_utctime
from src.logging import log
from src.metrics import *
from src.commit_timer import CommitTimer

@dataclass
class BatchContext:
    web3_router: any
    producer: any
    commit_timer: CommitTimer

    job_name: str
    run_id: str
    chain: str

    blocks_topic: str
    batch_tx_size: int

    blocks_value_serializer: callable


class BatchExecutor:
    def execute(
        self,
        ctx: BatchContext,
        batch_start: int,
        batch_end: int,
        range_size: int,
    ) -> dict:
        """
        Execute one batch.

        Returns:
            {
                "block_count": int,
                "tx_total": int,
            }
        """
        raise NotImplementedError


def fetch_range_with_metrics(web3_router, rs, re):
    task_start = time.perf_counter()
    thread = threading.current_thread()

    rpc_start = time.perf_counter()
    # provider return:  {"rpc": "alchemy","key_env": "ALCHEMY_API_KEY_3"}
    logs, provider_ctx = fetch_range_logs(
        web3_router,
        rs,
        re,
        with_provider=True,
    )

    rpc_cost_sec = time.perf_counter() - rpc_start
    
    task_cost_sec = time.perf_counter() - task_start

    return {
        "range_start": rs,
        "range_end": re,
        "logs": logs,
        "rpc": provider_ctx.rpc,
        "key_env": provider_ctx.key_env,
        "rpc_cost_sec": rpc_cost_sec,
        "task_cost_sec" : task_cost_sec,
        "worker_thread": thread.name,
        "worker_thread_id": thread.ident,
    }



class ParallelBatchExecutor(BatchExecutor):
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def execute(
        self,
        ctx: BatchContext,
        batch_start: int,
        batch_end: int,
        range_size: int,
    ):
        batch_tx_total = 0
        block_count = 0

        # -----------------------------
        # build ranges
        # -----------------------------
        ranges = []
        for range_start in range(batch_start, batch_end + 1, range_size):
            range_end = min(range_start + range_size - 1, batch_end)
            ranges.append((range_start, range_end))

        # -----------------------------
        # parallel fetch
        # -----------------------------
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:

            future_map = {
                pool.submit(
                    fetch_range_with_metrics,
                    ctx.web3_router,
                    rs,
                    re,
                ): (rs, re)
                for rs, re in ranges
            }

            for future in as_completed(future_map):
                rs, re = future_map[future]
                try:
                    result = future.result()
                    
                    task_cost = result.get("task_cost_sec")
                    
                    log.info(
                        "range_fetch_done",
                        extra={
                            # "chain": ctx.chain,
                            # "job": ctx.job_name,
                            "range_start": result["range_start"],
                            "range_end": result["range_end"],
                            # "worker": result["worker_thread"],
                            # "worker_thread_id": result["worker_thread_id"],
                            "rpc": result["rpc"],
                            "key_env": result["key_env"],
                            "cost_sec": round(task_cost, 2) if task_cost is not None else None,
                            "logs": len(result["logs"]) if result["logs"] else 0,
                        },
                    )
                    rpc_cost_sec = round(task_cost, 2) if task_cost is not None else 0
                    RPC_LATENCY.labels(chain=ctx.chain, rpc=result["rpc"]).observe(rpc_cost_sec) # histogram (time series)
                    RPC_LATENCY_LATEST.labels(chain=ctx.chain, rpc=result["rpc"]).set(rpc_cost_sec) # stat
                    
                    results.append(
                        (
                            result["range_start"],
                            result["range_end"],
                            result["logs"],
                        )
                    )

                except Exception as e:
                    log.exception(
                        "❌range_fetch_failed",
                        extra={
                            "chain": ctx.chain,
                            "job": ctx.job_name,
                            "range_start": rs,
                            "range_end": re,
                            "error": str(e)[:200],
                        },
                    )
                    raise

        # -----------------------------
        # deterministic order (important!)
        # -----------------------------
        results.sort(key=lambda x: x[0])

        # -----------------------------
        # reuse serial produce logic
        # -----------------------------
        for rs, re, range_logs in results:
            range_logs_safe = to_json_safe(range_logs)
            if not isinstance(range_logs_safe, list):
                raise RuntimeError("Unexpected range_logs type")

            logs_by_block = {}
            for log_item in range_logs_safe:
                bn = log_item.get("blockNumber")
                if bn is None:
                    continue
                if isinstance(bn, str):
                    bn = int(bn, 16)
                logs_by_block.setdefault(bn, []).append(log_item)

            for bn, transactions in logs_by_block.items():
                total_tx = len(transactions)
                batch_tx_total += total_tx
                block_count += 1

                for start_idx in range(0, total_tx, ctx.batch_tx_size):
                    batch_tx = transactions[start_idx : start_idx + ctx.batch_tx_size]

                    for idx, tx in enumerate(batch_tx, start=start_idx):
                        tx_record = {
                            "block_height": bn,
                            "job_name": ctx.job_name,
                            "run_id": ctx.run_id,
                            "inserted_at": current_utctime(),
                            "raw": json.dumps(tx),
                            "tx_index": idx,
                        }

                        ctx.producer.produce(
                            topic=ctx.blocks_topic,
                            key=f"{bn}-{idx}",
                            value=ctx.blocks_value_serializer(
                                tx_record,
                                SerializationContext(
                                    ctx.blocks_topic, MessageField.VALUE
                                ),
                            ),
                            on_delivery=delivery_report,
                        )

                    ctx.producer.poll(0)

                BLOCK_PROCESSED.labels(chain=ctx.chain, job=ctx.job_name).inc()
                TX_PROCESSED.labels(chain=ctx.chain, job=ctx.job_name).inc(total_tx)
                TX_PER_BLOCK.labels(chain=ctx.chain, job=ctx.job_name).observe(total_tx)

        # log.info(
        #     "batch_fetch_summary",
        #     extra={
        #         "chain": ctx.chain,
        #         "job": ctx.job_name,
        #         "batch_start": batch_start,
        #         "batch_end": batch_end,
        #         "range_count": len(ranges),
        #         "max_workers": self.max_workers,
        #     },
        # )

        return {
            "block_count": block_count,
            "tx_total": batch_tx_total,
        }