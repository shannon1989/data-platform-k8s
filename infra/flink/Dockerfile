FROM flink:1.20

# 安装 Python
USER root
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    python --version

# 安装 PyFlink（版本一定要匹配 Flink）
RUN pip3 install apache-flink==1.20

# Kafka SQL connector
RUN wget -P /opt/flink/lib \
  https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.4.0-1.20/flink-sql-connector-kafka-3.4.0-1.20.jar && \
  wget -P /opt/flink/lib \
  https://repo1.maven.org/maven2/org/apache/flink/flink-json/1.20.0/flink-json-1.20.0.jar


RUN set -eux; \
  curl -fLo /opt/flink/lib/flink-avro-confluent-registry-1.20.3.jar \
    https://repo1.maven.org/maven2/org/apache/flink/flink-avro-confluent-registry/1.20.3/flink-avro-confluent-registry-1.20.3.jar

USER flink