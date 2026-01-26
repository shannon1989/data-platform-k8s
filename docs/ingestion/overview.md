```mermaid
flowchart TD
    %% =====================
    %% Blockchain Networks
    %% =====================
    subgraph CHAINS["Blockchain Networks"]
        BSC["BSC"]
        ETH["Ethereum"]
        SOLANA["Solana"]
        SUI["Sui"]
    end

    %% =====================
    %% Kubernetes Ingestion Layer
    %% =====================
    subgraph K8S["Kubernetes Cluster"]
        direction TB

        subgraph BSC_INGEST["BSC Ingestion (Deployments / Pods)"]
            BSC_LOGS["bsc-pod-logs<br/>Async RPC Logs Ingestion"]
            BSC_BLOCKS["bsc-pod-blocks<br/>Block Ingestion"]
            BSC_TX["bsc-pod-tx<br/>Transaction Ingestion"]
            BSC_RECEIPTS["bsc-pod-receipts<br/>Receipt Ingestion"]
        end

        subgraph ETH_INGEST["ETH Ingestion (Deployments / Pods)"]
            ETH_LOGS["eth-pod-logs"]
            ETH_BLOCKS["eth-pod-blocks"]
            ETH_TX["eth-pod-tx"]
            ETH_RECEIPTS["eth-pod-receipts"]
        end
    end

    %% =====================
    %% Kafka Layer
    %% =====================
    %% subgraph KAFKA["Kafka Cluster "]


        subgraph KAFKA_RAW_TOPICS["Kafka - Raw Topics"]
        RAW_TOPICS["Raw Topics<br/>bsc.logs.raw<br/>bsc.blocks.raw<br/>eth.logs.raw<br/>..."]
        end


        subgraph KAFKA_TRANS_TOPICS["Kafka - Transformed Topics "]

        TRANS_TOPICS["Transformed Topics<br/>bsc.logs.transformed<br/>erc20.transfer<br/>..."]
        end
    %% end

    %% =====================
    %% Flink Stream Processing
    %% =====================
    subgraph FLINK["Flink on K8s"]
        FLINK_JOB["Flink Streaming Jobs<br/>• Parse / Decode<br/>• Drop Redundant Fields<br/>• Normalize Schema<br/>• Increase Info Density"]
    end

    %% =====================
    %% Data Lake / Iceberg
    %% =====================
    subgraph DATALAKE["Iceberg Data Lake"]
        direction TB
        SILVER["Silver Layer<br/>Cleaned / Structured Logs"]
        GOLD["Gold Layer<br/>Aggregated / Business Models"]
    end

    %% =====================
    %% Object Storage
    %% =====================
    S3["S3 / S3-Compatible Object Storage<br/>(AWS S3 / MinIO)"]

    %% =====================
    %% Compute / Query
    %% =====================
    subgraph QUERY["Query & Compute"]
        SparkSQL/PySpark["Spark SQL<br/>Batch / Streaming"]
        TRINO["Trino<br/>Interactive Analytics"]
    end

    %% =====================
    %% Consumers
    %% =====================
    subgraph CONSUMERS["Downstream Consumers"]
        METABASE["Metabase / BI Dashboards"]
        API["REST API / Data Service"]
    end

    %% =====================
    %% Connections
    %% =====================
    BSC --> BSC_LOGS
    BSC --> BSC_BLOCKS
    BSC --> BSC_TX
    BSC --> BSC_RECEIPTS

    ETH --> ETH_LOGS
    ETH --> ETH_BLOCKS
    ETH --> ETH_TX
    ETH --> ETH_RECEIPTS

    BSC_LOGS --> RAW_TOPICS
    BSC_BLOCKS --> RAW_TOPICS
    BSC_TX --> RAW_TOPICS
    BSC_RECEIPTS --> RAW_TOPICS

    ETH_LOGS --> RAW_TOPICS
    ETH_BLOCKS --> RAW_TOPICS
    ETH_TX --> RAW_TOPICS
    ETH_RECEIPTS --> RAW_TOPICS

    RAW_TOPICS --> FLINK_JOB
    FLINK_JOB --> TRANS_TOPICS

    TRANS_TOPICS --> SPARK_ENGINE
    SPARK_ENGINE --> SILVER
    SILVER --> GOLD

    SILVER --> S3
    GOLD --> S3

    S3 --> TRINO
    S3 --> SPARK_ENGINE

    TRINO --> METABASE
    TRINO --> API

```