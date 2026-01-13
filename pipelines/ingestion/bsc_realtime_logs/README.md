
```TXT
main.py (入口)
│
├─ fetch_and_push() [fetch_push_loop.py]
│    ├─ resolve_start_block() [state.py]        ← 获取上一次 checkpoint
│    ├─ fetch_block_logs(web3_router) [web3_utils.py]   ← Web3 RPC 调用
│    ├─ to_json_safe() [web3_utils.py]         ← 数据安全转换
│    ├─ Kafka producer [kafka_utils.py]        ← produce blocks & state
│    │    ├─ init_producer()
│    │    ├─ get_serializers()
│    │    └─ delivery_report()
│    ├─ Prometheus metrics [metrics.py]        ← 更新 block/tx/lag 指标
│    │    ├─ CHECKPOINT_BLOCK
│    │    ├─ CHAIN_LATEST_BLOCK
│    │    ├─ CHECKPOINT_LAG
│    │    ├─ BLOCK_PROCESSED
│    │    ├─ TX_PROCESSED
│    │    └─ TX_PER_BLOCK
│    └─ logging [logging.py]                   ← JSON 日志
│
├─ Web3Router + RpcPool + RpcProvider [rpc_provider.py]
│    ├─ pick() / _rebuild_queue()             ← RPC 轮询和负载权重
│    ├─ call(fn)                              ← RPC 调用封装 + 错误处理
│    └─ reward()/penalize()                   ← RPC健康管理
│
└─ time_utils.py
     └─ current_utctime()                     ← 时间戳生成
```