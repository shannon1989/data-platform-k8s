from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import *

spark = (
    SparkSession.builder
    .appName("silver_bsc_transactions_incremental")
    .getOrCreate()
)

# read max offset of silver
def get_silver_max_offset(table_name: str) -> int:
    if not spark.catalog.tableExists(table_name):
        return -1

    row = (
        spark.table(table_name)
        .agg(F.max("kafka_offset").alias("max_offset"))
        .collect()
    )[0]

    return row["max_offset"] if row["max_offset"] is not None else -1

# utility function
def hex_to_long(col):
    return F.conv(F.regexp_replace(col, "^0x", ""), 16, 10).cast("long")


SILVER_TABLE = "silver.bsc_mainnet_transactions"

silver_max_offset = get_silver_max_offset(SILVER_TABLE)
print(f"[Silver] current max kafka_offset = {silver_max_offset}")


# read incremental bronze data
BRONZE_TABLE = "bronze.bsc_mainnet_transactions"

bronze_inc = (
    spark.table(BRONZE_TABLE)
    .filter(F.col("kafka_offset") > silver_max_offset)
)

if bronze_inc.rdd.isEmpty():
    print("[Silver] No new bronze data, exit")
    spark.stop()
    exit(0)
    
    
def transform_bronze_to_silver(df):

    json_schema = StructType([
        StructField("blockHash", StringType()),
        StructField("blockNumber", StringType()),
        StructField("from", StringType()),
        StructField("to", StringType()),
        StructField("nonce", StringType()),
        StructField("hash", StringType()),
        StructField("transactionIndex", StringType()),
        StructField("value", StringType()),
        StructField("gas", StringType()),
        StructField("gasPrice", StringType()),
        StructField("maxFeePerGas", StringType()),
        StructField("maxPriorityFeePerGas", StringType()),
        StructField("input", StringType()),
        StructField("type", StringType()),
        StructField("accessList", ArrayType(
            StructType([
                StructField("address", StringType()),
                StructField("storageKeys", ArrayType(StringType()))
            ])
        )),
        StructField("chainId", StringType()),
        StructField("v", StringType()),
        StructField("r", StringType()),
        StructField("s", StringType()),
        StructField("yParity", StringType()),
    ])

    parsed = (
        df
        .withColumn("tx", F.from_json("raw", json_schema))
        .filter(F.col("tx.hash").isNotNull())
    )

    silver = (
        parsed
        .select(
            # Kafka & ingestion metadata
            "block_height",
            "job_name",
            "run_id",
            "kafka_topic",
            "kafka_partition",
            "kafka_offset",
            "kafka_timestamp",
            "kafka_date",

            # Transaction identity
            F.col("tx.hash").alias("tx_hash"),
            F.col("tx.blockHash").alias("block_hash"),
            hex_to_long(F.col("tx.blockNumber")).alias("block_number"),
            hex_to_long(F.col("tx.transactionIndex")).cast("int").alias("tx_index"),
            hex_to_long(F.col("tx.nonce")).alias("nonce"),
            F.col("tx.from").alias("from_address"),
            F.col("tx.to").alias("to_address"),

            # ---- Value & gas ----
            hex_to_long(F.col("tx.value")).cast("decimal(38,0)").alias("value_wei"),
            hex_to_long(F.col("tx.gas")).alias("gas_limit"),
            hex_to_long(F.col("tx.gasPrice")).alias("gas_price"),
            hex_to_long(F.col("tx.maxFeePerGas")).alias("max_fee_per_gas"),
            hex_to_long(F.col("tx.maxPriorityFeePerGas")).alias("max_priority_fee_per_gas"),

            # ---- Type & chain ----
            F.col("tx.type").alias("tx_type"),
            hex_to_long(F.col("tx.chainId")).cast("int").alias("chain_id"),

            # ---- Signature ----
            F.col("tx.v").alias("sig_v"),
            F.col("tx.r").alias("sig_r"),
            F.col("tx.s").alias("sig_s"),
            F.col("tx.yParity").alias("y_parity"),

            # ---- Input ----
            F.col("tx.input").alias("input_data"),
        )
        .withColumn("has_input", F.col("input_data") != "0x")
        .withColumn("method_id", F.when(F.col("has_input"), F.substring("input_data", 1, 10)))
        .withColumn("input_length", F.length("input_data"))
        .withColumn("input_words", (F.col("input_length") - 2) / 64)
        .withColumn("input_hash", F.sha2("input_data", 256))
        .withColumn("is_proxy_like", F.col("method_id").isin("0x5c60da1b", "0x3659cfe6")
        )
        .withColumn(
            "tx_kind",
            F.when(F.col("to_address").isNull(), "contract_creation")
            .when(F.col("input_data") == "0x", "transfer")
            .otherwise("contract_call")
        )
        .withColumn(
            "is_contract_call",
            F.col("input_data") != "0x"
        )
        .withColumn(
            "fee_model",
            F.when(F.col("tx_type") == "0x2", "eip1559")
            .when(F.col("tx_type") == "0x1", "access_list")
            .otherwise("legacy")
        )
    )

    return silver
  
  
silver_inc = transform_bronze_to_silver(bronze_inc)


(
    silver_inc
    .write
    .format("iceberg")
    .mode("append")
    .saveAsTable(SILVER_TABLE)
)

print(f"[Silver] appended {silver_inc.count()} rows")