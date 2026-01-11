FROM quay.io/jupyter/base-notebook:python-3.11

USER root

# ================= Java =================
RUN apt-get update && apt-get install -y openjdk-17-jdk-headless wget curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# ================= Spark =================
ENV SPARK_VERSION=3.5.1
ENV HADOOP_VERSION=3

RUN wget -q https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    tar -xzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    mv spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} /opt/spark && \
    rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz

ENV SPARK_HOME=/opt/spark
ENV PATH=$SPARK_HOME/bin:$PATH

# ================= Spark JARs =================
RUN mkdir -p $SPARK_HOME/jars

# Iceberg
RUN wget -q -P $SPARK_HOME/jars \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.5.2/iceberg-spark-runtime-3.5_2.12-1.5.2.jar

# Hadoop AWS
RUN wget -q -P $SPARK_HOME/jars \
    https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar

# AWS SDK
RUN wget -q -P $SPARK_HOME/jars \
    https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar

# Spark Kafka & Avro
RUN wget -q -P $SPARK_HOME/jars \
      https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.1/spark-sql-kafka-0-10_2.12-3.5.1.jar && \
    wget -q -P $SPARK_HOME/jars \
      https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.1/spark-token-provider-kafka-0-10_2.12-3.5.1.jar && \
    wget -q -P $SPARK_HOME/jars \
      https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.6.1/kafka-clients-3.6.1.jar && \
    wget -q -P $SPARK_HOME/jars \
      https://repo1.maven.org/maven2/org/apache/spark/spark-avro_2.12/3.5.1/spark-avro_2.12-3.5.1.jar && \
    wget -q -P $SPARK_HOME/jars \
      https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.0/commons-pool2-2.12.0.jar && \
    wget -q -P $SPARK_HOME/jars \
      https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.14.0/commons-lang3-3.14.0.jar

# ================= Python deps =================
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ================= Spark defaults Config (Iceberg + MinIO) =================
COPY spark-defaults.conf $SPARK_HOME/conf/spark-defaults.conf

# ================= Hadoop metrics empty config =================
RUN touch $SPARK_HOME/conf/hadoop-metrics2.properties && \
    touch $SPARK_HOME/conf/hadoop-metrics2-s3a-file-system.properties

# ================= clean home =================
RUN rm -rf /home/jovyan/*

USER jovyan
