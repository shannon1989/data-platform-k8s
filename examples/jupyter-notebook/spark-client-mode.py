import os
from pyspark.sql import SparkSession

driver_ip = os.popen("hostname -i").read().strip()
# Driver is inside Notebook 容器内（不是 K8s Pod）

spark = SparkSession.builder \
    .appName("NotebookToK8s") \
    .master("k8s://https://kubernetes.default.svc") \
    .config("spark.kubernetes.namespace", "airflow") \
    .config("spark.kubernetes.container.image", "docker.io/library/spark:4.0.0") \
    .config("spark.driver.host", driver_ip) \
    .config("spark.driver.bindAddress", "0.0.0.0") \
    .config("spark.driver.port", "7078") \
    .config("spark.kubernetes.authenticate.driver.serviceAccountName", "default") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://http://minio.airflow.svc.cluster.local:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()