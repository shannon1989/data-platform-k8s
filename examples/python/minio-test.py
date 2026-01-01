from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *


spark = (
    SparkSession.builder
    .appName("nb-minio-test")
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .getOrCreate()
)

data = [
    ("James", "Smith", "36636", "M", 3000),
    ("Michael", "Rose", "40288", "M", 4000),
    ("Robert", "Williams", "42114", "M", 4000),
    ("Maria", "Jones", "39192", "F", 4000),
    ("Jen", "Brown", "39193", "F", -1)
]

schema = StructType(
    [
        StructField("first_name", StringType(), True),
        StructField("last_name", StringType(), True),
        StructField("id", StringType(), True),
        StructField("gender", StringType(), True),
        StructField("salary", IntegerType(), True),
    ]
)

df = spark.createDataFrame(data, schema)

df.write.mode("overwrite").parquet("s3a://datalake/bronze/notebook_minio_test")