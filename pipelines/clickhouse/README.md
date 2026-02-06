
| 需求               | 结论          |
| ---------------- | ----------- |
| 100ms 级 SLA      | ❌ Spark 不合适 |
| 实时告警 / CEP       | ❌ Spark 不合适 |
| 秒级 BI / 看板       | ✅ Spark 很合适 |
| 大吞吐写入            | ✅ Spark 很合适 |
| 复杂 SQL transform | ✅ Spark 很合适 |

```TXT
Kafka
 ├─ Spark → Iceberg      （事实层 / 回放） - processTime = 60 seconds
 └─ Spark → ClickHouse   （秒级 OLAP）     - processTime = 1 seconds
```

| 名词            | 行业实际含义        |
| ------------- | ------------- |
| Real-time     | <100ms        |
| Streaming     | <1s           |
| Near realtime | 几十秒 ~ 几分钟 |
| Batch         | ≥ 5–10 分钟     |


| 路径                      | 延迟           |
| ----------------------- | ------------ |
| Kafka → ClickHouse      | **100ms～1s** |
| Kafka → Spark → Iceberg | 10s～分钟       |
| Kafka → Flink → Iceberg | 2～5s（优化后）    |



```sql
CREATE DATABASE IF NOT EXISTS bsc
ON CLUSTER analytics;
```

1️⃣ Kafka Engine 表（只做 ingestion，不存数据）
- ClickHouse 里的 Kafka Consumer
- local table
```sql
CREATE TABLE kafka.bsc_transactions_kafka_consumer
on cluster analytics
(
    -- Avro value（完整反序列化）
    -- ========= 业务字段 =========
    block_height    Int64,
    job_name        String,
    run_id          String,
    raw             String
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'redpanda.kafka.svc:9092',
    kafka_topic_list  = 'blockchain.bsc.ingestion.transactions.raw',
    kafka_group_name  = 'ch_bsc_transactions_consumer',
    kafka_format      = 'AvroConfluent',
    format_avro_schema_registry_url  = 'http://redpanda.kafka.svc:8081',
    kafka_num_consumers = 1;
```
```sql
SET stream_like_engine_allow_direct_select = 1;
SELECT * from kafka.bsc_mainnet_transactions_raw limit 1;
```
### 实际存储表（存数据）
2️⃣ 真正落盘的表（MergeTree）引擎表
```sql
CREATE TABLE kafka.bsc_transactions_raw
on cluster analytics
(
    -- ========= 业务字段 =========
    block_height      Int64,
    job_name          String,
    run_id            String,
    raw               String,

    -- ========= Kafka 元数据 =========
    kafka_key       String,
    kafka_partition   Int32,
    kafka_offset      Int64,
    kafka_timestamp   DateTime64(3),
    kafka_date        Date
)
ENGINE = MergeTree
PARTITION BY kafka_date
ORDER BY (block_height, kafka_partition, kafka_offset)
SETTINGS index_granularity = 8192;
```

3️⃣ Materialized View（真正的数据通道）
```sql
CREATE MATERIALIZED VIEW kafka.mv_kafka_bsc_transactions_raw
on cluster analytics
TO kafka.bsc_transactions_raw
AS
SELECT
    block_height,
    job_name,
    run_id,
    raw,

    _key as kafka_key,
    _partition AS kafka_partition,
    _offset    AS kafka_offset,
    _timestamp AS kafka_timestamp,
    toDate(_timestamp) AS kafka_date    
FROM kafka.bsc_transactions_kafka_consumer;
```

4️⃣ Distributed 表（对外查询用）
- 逻辑表，本身不存数据; 必须 `ON CLUSTER`
```sql
CREATE TABLE bsc.mainnet_transactions_raw
on cluster analytics
AS kafka.bsc_transactions_raw
ENGINE = Distributed(
    analytics,
    kafka,
    bsc_transactions_raw,
    kafka_partition
);
```
kafka_num_consumers 尽量不要 > 1，吞吐靠 shard 扩
👉 最稳妥的 scaling 方式：增加 shard, 而不是增加 kafka_num_consumers

## Summary
- Kafka Engine 表是 local 的，ON CLUSTER 仅用于 DDL 分发；
- 实际 Kafka consumer 数 = shard × replica × kafka_num_consumers；
- 该值必须 ≤ topic partition 数，否则会导致 rebalance 和吞吐下降；
- 生产环境中优先通过 增加 shard 而非 增加 kafka_num_consumers 来扩展吞吐。

```sql
-- 看每个 shard 各有多少
SELECT
    hostName(),
    count(*)
FROM clusterAllReplicas('analytics', kafka.bsc_transactions_raw)
GROUP BY hostName();
```
```TXT
Local 表：必须 ON CLUSTER
Kafka 表：必须 ON CLUSTER
Materialized View：必须 ON CLUSTER
Distributed 表：如果对外查，必须 ON CLUSTER
```

SELECT * FROM system.kafka_consumers;


-- 当前内存
SELECT formatReadableSize(value)
FROM system.metrics
WHERE metric = 'MemoryTracking';

-- 最大峰值
SELECT formatReadableSize(value)
FROM system.events
WHERE event = 'MemoryTrackerPeak';

-- 谁在用
SELECT *
FROM system.processes
ORDER BY memory_usage DESC;
