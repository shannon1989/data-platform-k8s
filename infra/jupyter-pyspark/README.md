# Installing jupyter / minio / iceberg / kafka / web3 on Kubernetes

## pull image - using base image and add other packages
```bash
docker quay.io/jupyter/base-notebook:python-3.11
```

## Create spark-defaults.conf
1. Register spark_catalog as the default Iceberg
2. Setup Iceberg root directory s3a://datalake in Minio
3. Setup default minio endpoint
4. Using icerberg as the default type.
```BASH
# Iceberg SQL extenstions
spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions

# Point `spark_catalog` to the Iceberg `SessionCatalog`
spark.sql.catalog.spark_catalog=org.apache.iceberg.spark.SparkSessionCatalog
spark.sql.catalog.spark_catalog.type=hadoop
spark.sql.catalog.spark_catalog.warehouse=s3a://datalake

# default table format iceberg
spark.sql.catalog.spark_catalog.catalog-impl=org.apache.iceberg.spark.SparkSessionCatalog
spark.sql.catalog.spark_catalog.default-namespace=default
spark.sql.catalog.spark_catalog.default-namespace.type=iceberg

# S3/Minio config
spark.hadoop.fs.s3a.endpoint=http://minio.airflow:9000
spark.hadoop.fs.s3a.access.key=minioadmin
spark.hadoop.fs.s3a.secret.key=minioadmin
spark.hadoop.fs.s3a.path.style.access=true
spark.hadoop.fs.s3a.connection.ssl.enabled=false
spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem
```



build custom image
```bash
eval $(minikube docker-env) # for minikube
docker build -t jupyter-data-platform:0.1.2 .

kind load docker-image jupyter-data-platform:0.1.6 # for kind
```

```bash
kubectl create ns airflow
kubectl apply -f jupyter-pvc.yaml
kubectl apply -f jupyter-notebook.yaml
```

reload same image tag when the image is rebuid.
kubectl rollout restart deploy/jupyter-pyspark -n airflow


mkdir -p jars
wget https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.5.2/iceberg-spark-runtime-3.5_2.12-1.5.2.jar -P jars/
wget https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar -P jars/
wget https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar -P jars/
wget https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.1/spark-sql-kafka-0-10_2.12-3.5.1.jar -P jars/
wget https://repo1.maven.org/maven2/org/apache/spark/spark-avro_2.12/3.5.1/spark-avro_2.12-3.5.1.jar -P jars/
wget https://repo1.maven.org/maven2/io/confluent/kafka-avro-serializer/7.4.1/kafka-avro-serializer-7.4.1.jar -P jars/
wget https://repo1.maven.org/maven2/io/confluent/common-config/7.4.1/common-config-7.4.1.jar -P jars/
wget https://repo1.maven.org/maven2/io/confluent/common-utils/7.4.1/common-utils-7.4.1.jar -P jars/

if failed:
wget https://packages.confluent.io/maven/io/confluent/kafka-avro-serializer/7.4.1/kafka-avro-serializer-7.4.1.jar -P jars/
wget https://packages.confluent.io/maven/io/confluent/common-config/7.4.1/common-config-7.4.1.jar -P jars/
wget https://packages.confluent.io/maven/io/confluent/common-utils/7.4.1/common-utils-7.4.1.jar -P jars/
