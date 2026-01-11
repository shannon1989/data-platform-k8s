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
eval $(minikube docker-env) # for minikube only
docker build -t jupyter-data-platform:0.1.2 .
```

```bash
kubectl create ns jupyter-pyspark
kubectl apply -f jupyter-pvc.yaml
kubectl apply -f jupyter-pyspark.yaml
```

reload same image tag when the image is rebuid.
kubectl rollout restart deploy/jupyter-pyspark -n airflow
