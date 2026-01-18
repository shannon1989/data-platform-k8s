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