# data-platform-k8s

A modern data platform on Kubernetes integrating batch and streaming processing, object storage, and BI visualization.

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
├── infra/        # Airflow, Spark, Kafka, MinIO, Metabase, ClickHouse, Prometheus, Grafana
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
