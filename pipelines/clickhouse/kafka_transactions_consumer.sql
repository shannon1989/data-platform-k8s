-- single node clickhouse cluster kafka stream ingestion
-- 100K TPS for single consumer with single partition in kafka topic with peak memory usage 5G.
--1.create engine table
CREATE TABLE bsc.transactions_kafka_consumer
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

--2. create target table
CREATE TABLE bsc.transactions_raw
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

--3. create pipeline materialized view
CREATE MATERIALIZED VIEW bsc.mv_transactions_raw_pipeline
TO bsc.transactions_raw
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
FROM bsc.transactions_kafka_consumer;