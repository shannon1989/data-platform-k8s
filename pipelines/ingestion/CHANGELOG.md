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

## [x.x.x] - 2026-Jan/Feb/Mar (plan)
### planned
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