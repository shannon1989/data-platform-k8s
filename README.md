# data-platform-k8s

A data platform on Kubernetes integrating batch and streaming processing, object storage, and BI visualization.

---

## 🚀 Overview

`data-platform-k8s` is a Kubernetes-based data platform designed to demonstrate real-world data engineering workflows, including:

- Batch and streaming data processing
- Workflow orchestration
- Object storage with S3 compatibility
- SQL-based analytics and BI visualization
- Local-first development using Minikube

This project focuses on **practical, reproducible, and production-aligned setups**, rather than toy examples.

---

## 🧱 Architecture

**Core idea:**  
Kafka ingests data → Spark processes data → MinIO stores data → BI tools visualize results  
All workflows are orchestrated by Airflow and run natively on Kubernetes.

> The platform is modular: each component can be deployed, upgraded, or replaced independently.

---

## 🔧 Tech Stack

- **Container & Orchestration**
  - Kubernetes (Minikube)
  - Docker

- **Data Processing**
  - Apache Spark (Spark Operator)
  - Batch & Streaming Jobs

- **Workflow Orchestration**
  - Apache Airflow (Kubernetes Executor)

- **Messaging**
  - Apache Kafka (Strimzi)

- **Storage**
  - MinIO (S3-compatible object storage)

- **Analytics & BI**
  - Metabase

---

## 📁 Repository Structure

```text
data-platform-k8s/
├── apps/         # Airflow, Spark, Kafka, MinIO, Metabase, ClickHouse
├── images/       # Custom Docker images (Spark, ClickHouse, Airflow)
├── scripts/      # Deployment and operational scripts
├── examples/     # Example Spark jobs and ETL pipelines
├── docs/         # Architecture and design documents
└── env/          # Environment-specific configs (local/dev/prod)
```

---


## 🎯 Design Goals

- Production-oriented: avoids shortcuts that break in real clusters

- Modular & extensible: easy to add ClickHouse, Trino, Flink, etc.

- Local-first: everything can run on a laptop using Minikube (config required)

- GitOps-friendly: declarative configs and reproducible deployments

## 📌 Use Cases

- End-to-end data engineering demos

- Kubernetes-native Spark & Airflow integration

- Streaming + batch hybrid pipelines

- Portfolio project for Data Engineer / Platform Engineer roles

## 🛠️ Future Enhancements

- ClickHouse / Trino integration

- Data quality checks

- Monitoring with Prometheus & Grafana

- CI/CD for image builds and deployments


Suggestion from :

data-platform-k8s/
├── apps/                 # Airflow, Spark, Kafka, MinIO, ClickHouse
├── images/               # Custom Docker images
├── scripts/              # 运维 / 安装 / bootstrap 脚本
├── examples/             # Demo / PoC / 教学示例
├── docs/                 # 架构 & 设计文档
├── .env/                 # 环境变量 / values
│
├── pipelines/            # 🔥🔥🔥 数据逻辑核心（重点）
│   ├── ingestion/
│   │   └── sui/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── client.py        # Sui RPC / REST
│   │       ├── producer.py      # Kafka / Redpanda
│   │       ├── checkpoints.py   # 断点 / offset 管理
│   │       ├── fetch_tx.py      # 纯逻辑
│   │       └── main.py          # CLI / Airflow 入口
│   │
│   ├── transform/
│   │   ├── spark/
│   │   │   └── sui/
│   │   │       ├── job.py
│   │   │       └── schema.py
│   │   └── python/
│   │       └── normalize/
│   │           └── sui_tx.py
│   │
│   ├── load/
│   │   └── clickhouse/
│   │       ├── tables.sql
│   │       └── load_from_kafka.py
│   │
│   └── dbt/
│       ├── dbt_project.yml
│       ├── profiles.yml
│       ├── models/
│       │   ├── staging/
│       │   ├── marts/
│       │   └── metrics/
│       └── macros/
│
├── requirements.txt
└── README.md
