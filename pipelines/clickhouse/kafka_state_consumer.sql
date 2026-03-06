--1.create engine table
CREATE OR REPLACE TABLE bsc.state_kafka_consumer
(
    -- Avro value（完整反序列化）
    -- ========= 业务字段 =========
    checkpoint    Int64,
    producer Tuple(
        pod_uid String,
        pod_name String
    ),

    run Tuple(
        run_id String,
        mode String,
        started_at String,
        start_block Int64
    )
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'redpanda.kafka.svc:9092',
    kafka_topic_list  = 'blockchain.ingestion._state',
    kafka_group_name  = 'ch_bsc_state_consumer',
    kafka_format      = 'AvroConfluent',
    format_avro_schema_registry_url  = 'http://redpanda.kafka.svc:8081',
    kafka_num_consumers = 1;

--2. create target table
CREATE OR REPLACE TABLE bsc.state
(
    -- ========= 业务字段 =========
    checkpoint      Int64,
    pod_uid         String,
    pod_name        String,
    run_id          String,
    mode            String,
    started_at      DateTime64(3),
    start_block     Int64,

    -- ========= Kafka 元数据 =========
    kafka_key       String,
    kafka_partition   Int32,
    kafka_offset      Int64,
    kafka_timestamp   DateTime64(3),
    kafka_date        Date
)
ENGINE = MergeTree
PARTITION BY kafka_date
ORDER BY (checkpoint, kafka_partition, kafka_offset)
SETTINGS index_granularity = 8192;

--3. create pipeline materialized view
CREATE MATERIALIZED VIEW bsc.mv_state_pipeline
TO bsc.state
AS
SELECT
    checkpoint,
    producer.1 AS pod_uid,
    producer.2 AS pod_name,
    run.1 AS run_id,
    run.2 AS mode,
    parseDateTime64BestEffort(run.3, 3) AS started_at,
    run.4 AS start_block,

    _key as kafka_key,
    _partition AS kafka_partition,
    _offset    AS kafka_offset,
    _timestamp AS kafka_timestamp,
    toDate(_timestamp) AS kafka_date
FROM bsc.state_kafka_consumer;