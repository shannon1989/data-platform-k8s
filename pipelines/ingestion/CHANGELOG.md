## [0.1.7] - 2026-01-17
### Changed
- Change log fetching from single block to range block

### Added
- commit_interval_sec metric
- rpc_cost_sec metric
- rpc_calls metric
- avg_rpc_cost metric (avg_rpc_cost = rpc_cost_sec / rpc_calls)
- Adaptive RPC routing logs


## [0.1.8] - 2026-01-17
### Changed
- RPC may return empty log list, add retry scheme

### Added
- Add retry for fetch_range_logs function
- Add web3_router.rotate_provider function


## [0.1.9] - 2026-01-18
### Changed
- Support a list of key for same RPC provider
- Batch executor abstration

### Added
- Add class BatchContext, BatchExecutor and SerialBatchExecutor


## [0.2.0] - 2026-01-18
### Changed
- Parallel executor abstration

### Added
- Add ParallelBatchExecutor for fetch_range_logs
- Add JOB_MODE and remove FROM_LAST_BLOCK env.


## [0.2.1] - 2026-01-19
### Changed
- Validate latest block from RPC
- Observibility for commit interval
- Add histogram and stat view of commit interval in Grafana
- Add monitor in RPC key_env level

### Added
- Add SafeLatestBlockProvider
- Add metrics: COMMIT_INTERVAL and COMMIT_INTERVAL_LATEST

## [0.2.2] - 2026-01-19
### Changed
- Add monitor in RPC key_env level

### Added
- Add build_url inside RpcProvider to receive the key_env variables
- Move build_rpc_pool from main program to RpcPool class

## [0.2.3] - 2026-01-19
### Changed
- Move rpc_context.py package to rpc_provider.py
- Group key into public and private, display rpc requests usage. (disply by key_env)

## [0.2.4] - 2026-01-20
### Changed
- Add monitor metrics for RPC latency of each provider
- New metrics: RPC_LATENCY(Histogram), RPC_LATENCY_LATEST(Gauge)


## [0.2.5] - 2026-01-20
### Changed
- Remove random.choice(key_env) from RpcPool.from_config
- Use key_env list fro RpcProvider and add slot for each key of a provider

## [0.2.6] - 2026-01-20
### Changed
- Print key_env in logs
- Return logs, RpcContext for Web3Router._call_internal method

## [0.2.7] - 2026-01-20
### Changed
- Bug fix for RpcKeySlot
- 同一个 key，在请求“执行期间”不可再次被 acquire
- Add emoji for log.warning, log.error, job_start, kafka_commit and range_fetch_done.

## [0.2.8] - 2026-01-20
### Changed
- Update logic: key will be used only once with the same batch
- No duplicate key/rpc within the same batch
- Add BatchKeyManager class
- Add RPC_KEY_BUSY metrics


## [0.2.9] - 2026-01-20
### Changed
- RPC active connection add active_rpc_connections

## [0.2.9] - 2026-01-21
### Changed
- Calculate COMMIT_COST_LATEST metric in Grafana
- Empty block log checking (eg: 76158470)
| 指标                      | 含义                      |
| ----------------------- | ----------------------- |
| `commit_interval_sec`   | 两次 commit 之间的间隔         |
| `commit_cost_sec`       | commit_transaction 本身耗时 |
| `commit_overhead_ratio` | commit 占 batch 的比例      |

## [1.0.0] - 2026-01-24
### Changed
- Architecture upgrade
- blockchain streaming ingestion - range retry/latest_block_no retry


## [1.0.1] - 2026-01-24
### Changed
- Add metrics/metricsContext/metricsRuntime
- Update Grafana dashboard, show ingested / committed logs per sec
- logs processing speed increased from 3K/s to 20k/s with inflight worker 10

## [1.0.1] - 2026-01-25
### Changed
- get_metrics() bug fix
- add RPC documentation

## [1.0.2] - 2026-01-26
### Changed
- Add metrics: range_inflight - 是否长期贴近 max_inflight_ranges
- Add metircs: backlog = rpc_submitted - rpc_finished
- Add metrics: rpc_key_unavailable_total (RPC key unavailable due to key_interval) - Time 维度是否成为瓶颈的“真相指标”
- Add metircs: Total RPC finished (success or error) 
- Add cooldown / Circuit Breaker / Half-Open

## [1.0.3/1.0.4] - 2026-01-27
### Changed
- Add realtime mode (resume_mod = "chain_head") : ingest from latest block onwards
- Add realtime mode (resume_mod = "checkpoint") : ingest from latest checkpoint
- Add safe latest chain head function: LatestBlockTracker
- Add methods_group in configMap. 
    - eth_blockNumber -> light method (public RPC)
    - eth_getLogs -> heavy method (private RPC)
- Kafka transactional_id issue fix - using POD_NAME
- Split realtime resume mode (resume from chain-head / resume from checkpoint - backfill mode)

## [1.0.5] - 2026-01-28
### Changed
  - Redesign Kafka topics to support: blocks, Tx, receipts, traces.
  - 


## [x.x.x] - 2026-Jan/Feb/Mar (plan)
### planned
- Adaptive range size for different RPC.
- Adaptive key_concurrency_per_batch.
- Output logs with rpc key_env
- Resolve RPC with extreming long latency
- Add Python Queue for Kafka backpressure.
- Add proxy router for RPC.
- Blockchain logs data model in Iceberg
- SparkOperator for structured streaming
- Lakehouse layer design (partition table - bronze/silver/gold)
- Distributed query engine - Trino deployment
- Airflow orchestration for logs
- Blockchain logs data deep analysis (batch and realtime)
- Bring Flink for realtime analysis.
- Add blocks/Tx/Receipts and orchestrated through Airflow