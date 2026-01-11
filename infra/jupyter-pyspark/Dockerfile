FROM quay.io/jupyter/base-notebook:python-3.11

USER root

# ========== Java ==========
RUN apt-get update && apt-get install -y openjdk-17-jdk wget && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# ========== Spark ==========
ENV SPARK_VERSION=3.5.1
ENV HADOOP_VERSION=3

RUN wget -q https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    tar -xzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    mv spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} /opt/spark && \
    rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz

ENV SPARK_HOME=/opt/spark
ENV PATH=$SPARK_HOME/bin:$PATH

# ========== Spark JARs ==========
RUN wget -P $SPARK_HOME/jars \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.5.2/iceberg-spark-runtime-3.5_2.12-1.5.2.jar && \
    wget -P $SPARK_HOME/jars \
    https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    wget -P $SPARK_HOME/jars \
    https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar

# ========== Spark defaults (Iceberg + MinIO) ==========
RUN mkdir -p $SPARK_HOME/conf && \
    echo "\
spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions\n\
spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog\n\
spark.sql.catalog.iceberg.type=hadoop\n\
spark.sql.catalog.iceberg.warehouse=s3a://datalake/iceberg\n\
\n\
spark.hadoop.fs.s3a.endpoint=http://minio.airflow.svc.cluster.local:9000\n\
spark.hadoop.fs.s3a.access.key=minioadmin\n\
spark.hadoop.fs.s3a.secret.key=minioadmin\n\
spark.hadoop.fs.s3a.path.style.access=true\n\
spark.hadoop.fs.s3a.connection.ssl.enabled=false\n\
spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem\n\
" > $SPARK_HOME/conf/spark-defaults.conf

# ========== Python deps ==========
RUN pip install --no-cache-dir pyspark==3.5.1 jupyterlab

USER jovyan


# This image can be used as below:
# Jupyter Notebook
# Airflow KubernetesPodOperator
# Spark Operator（driver/executor）