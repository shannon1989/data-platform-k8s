FROM jupyter/pyspark-notebook:latest

USER root

# Hadoop AWS + AWS SDK
RUN wget -P /usr/local/spark/jars \
    https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    wget -P /usr/local/spark/jars \
    https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar

USER jovyan

# jupyter/pyspark-notebook镜像默认不带云存储，需要自定义镜像
# 1. eval $(minikube docker-env)
# 2. docker build -t pyspark-minio:latest .
# 3. minikube image load pyspark-minio:latest
