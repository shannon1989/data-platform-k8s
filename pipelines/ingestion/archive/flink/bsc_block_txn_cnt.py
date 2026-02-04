# job.py
from pyflink.table import EnvironmentSettings, TableEnvironment

env_settings = EnvironmentSettings.in_streaming_mode()
t_env = TableEnvironment.create(env_settings)

# Kafka source
t_env.execute_sql("""
CREATE TABLE bsc_transactions_raw (
  block_height BIGINT,
  job_name STRING,
  run_id STRING,
  data STRING,
  proc_time AS PROCTIME()
) WITH (
  'connector' = 'kafka',
  'topic' = 'blockchain.bsc.ingestion.transactions.raw',
  'properties.bootstrap.servers' = 'redpanda.kafka.svc:9092',
  'properties.group.id' = 'flink_transactions_reader',
  'scan.startup.mode' = 'earliest-offset',

  'format' = 'avro-confluent',
  'avro-confluent.schema-registry.url' = 'http://redpanda.kafka.svc:8081'
)
""")

# Print sink（关键）
# t_env.execute_sql("""
# CREATE TABLE print_sink (
#   block_height BIGINT,
#   cnt BIGINT
# ) WITH (
#   'connector' = 'print'
# )
# """)

t_env.execute_sql("""
CREATE TABLE bsc_block_txn_cnt (
  block_height BIGINT,
  window_start TIMESTAMP(3),
  window_end TIMESTAMP(3),
  cnt BIGINT,
  PRIMARY KEY (block_height, window_start) NOT ENFORCED
) WITH (
  'connector' = 'upsert-kafka',
  'topic' = 'blockchain.bsc.flink.block_txn_cnt',
  'properties.bootstrap.servers' = 'redpanda.kafka.svc:9092',
  'key.format' = 'json',
  'value.format' = 'json'
)
""")


# Insert into sink（⚠️ streaming 一定要用 INSERT）
t_env.execute_sql("""
INSERT INTO bsc_block_txn_cnt
SELECT
  block_height,
  window_start,
  window_end,
  COUNT(*) AS cnt
FROM TABLE(
  TUMBLE(
    TABLE bsc_transactions_raw,
    DESCRIPTOR(proc_time),
    INTERVAL '10' SECOND
  )
)
GROUP BY block_height, window_start, window_end
""")
