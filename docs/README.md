# ClickHouse deployement and Prometheus config
  - Pipeline Orchestratio: Airflow 3.0, Dagster
  - ETL/ELT pipelines: Apache Spark, Kafka, Flink, ClickHouse, Jupyter Notebook
  - Data Observability: dbt, Great Expectations
  - Time-series Monitoring: Prometheus, Grafana
  - Data Visualization: Metabase
  - Object Stroage: MinIO, MongoDB
  - CI/CD: GitHub Actions
  - LLM, RAG, Vector Database
  - Tools: K9s, Helm, Git

## Introduction

This guide walks through the manual installation of Apache Airflow 3.0 with remote logging on MinIO on a Kubernetes cluster using Minikue.

It covers:
- Deploying Airflow, MinIO, Spark, Jupyter Notebook, Kafka, ClickHouse using Helm.
- Setting up Git synchronization for Airflow DAGs.
- Setting up Airflow remote logging with MioIO.
- Deploying Jupyter Notebook with PySpark for data exploration.
- Setting up observibility tool (dbt, Great Expectations, Dagster)
- Setting up time-series monitoring (Prometheus/Grafana)
- Setting up CI/CD using Github actions

Study Plan:
  | Date | Task | Note |
  |------|------|------|
  | 2025/12/31 | Airflow Trigger Custom Python Pipeline | Python Call API to extract data and stored in the MinIO | 
  | 2026/01/01 | Deploy Kafka to ingest the blockchain event stream data | Python Call API to extract data and stored in Kafka | 

## 1. Prepare the cluster wiht Minikube
```bash
minikube start --cpus=8 --memory=16g
```

## 2. Airflow 3.0 deployement
Create Airflow namespace
```bash
kubectl create ns airflow
```

Create SSH Key Secret for Git Access
```bash
ssh-keygen -t rsa -b 4096 -C "example@gmail.com" -f ./airflow_gitsync_id_rsa
```

Create a Kubernetes secret on airflow namespace from the private key
```bash
kubectl create secret generic airflow-git-ssh-key-secret \
--from-file=gitSshKey=./airflow_gitsync_id_rsa \
--namespace airflow 
--dry-run=client -o yaml > airflow-git-ssh-key-secret.yaml
```

Apply the secret to the Kubernetes cluster
```bash
kubectl apply -f airflow-git-ssh-key-secret.yaml
kubectl apply -f airflow-postgresql-credentials-secret.yaml
```
Add Deploy Key to Git Repository

> Copy the contents of airflow_gitsync_id_rsa.pub and add it as a Deploy Key with read-only access in your Git repository. [GitHub Deploy Key Docs](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys#deploy-keys)

Deploy Airflow
```bash
helm -n airflow upgrade --install airflow apache-airflow/airflow -f values.yaml
```

Port-forward and access Airflow Web Console: [http://localhost:8080](http://localhost:8080) (user: admin pass: admin)
```bash
kubectl -n airflow port-forward svc/airflow-api-server 8080:8080
```

## 3. MinIO Deployment:
```bash
kubectl apply -f minio.yaml
```
Port-forward and access MinIO Web Console: [http://localhost:9001](http://localhost:9001) (user: minioadmin pass: minioadmin)
```bash
kubectl port-forward -n airflow svc/minio 9001:9001
```


## 4. Airflow Remote logging MinIO Config
Login minio pod 
```bash
kubectl exec -it -n airflow deploy/minio -- sh
```

Create bucket
```bash
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/airflow-logs
mc policy set public local/airflow-logs
```

Airflow configuration with MinIO Connection
```bash
kubectl exec -it -n airflow deploy/airflow-api-server -- \
airflow connections add minio_conn \
--conn-type aws \
--conn-extra '{
    "aws_access_key_id": "minioadmin",
    "aws_secret_access_key": "minioadmin",
    "endpoint_url": "http://minio:9000"
}'
```

Validation：
```bash
kubectl exec -it -n airflow deploy/airflow-api-server -- airflow connections get minio_conn
```

Complete Airflow with MinIO YAML
```YAML
executor: "KubernetesExecutor" # Dynamically creates a Kubernetes pod for each task, reducing dependencies and improving scalability.
dags:
  persistence:
    enabled: false
  gitSync:
    enabled: true
    repo: ssh://git@ssh.github.com:443/shannon1989/data-analytics-platforms.git # URL of your Git repository containing the Airflow DAGs.
    branch: "main"
    rev: HEAD
    depth: 1
    wait: 60  # Sync every 60 seconds
    subPath: "dags" # subdirectory within the repository where the DAGs are located.
    containerName: "git-sync" 
    sshKeySecret: "airflow-git-ssh-key-secret" # Reference the Kubernetes secret containing the SSH private key for Git access
    knownHosts: |
      ssh.github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
redis:
  enabled: false  # Celery backend not needed when using KubernetesExecutor
postgresql:
  enabled: true
  image:
    repository: bitnamilegacy/postgresql # The bitnamilegacy repository is a temporary workaround, for prod-ready using Postgres Server
    tag: 16.1.0-debian-11-r15
  auth:
    enablePostgresUser: true
    username: "airflowuser" # metadata DB username
    database: airflow       # metadata DB name
    existingSecret: airflow-postgresql-credentials
data:
  metadataConnection:
    user: airflowuser           # metadata DB username
    pass: airflow_db_password   # metadata DB password
    protocol: postgresql+psycopg2
    host: airflow-postgresql
    port: 5432
    db: airflow
triggerer:
  replicas: 1
  persistence:
    size: 5Gi

# Config the MioIO remote logging.
config:
  logging:
    remote_logging: "True"
    remote_base_log_folder: "s3://airflow-logs"
    remote_log_conn_id: "minio_conn"
    encrypt_s3_logs: "False"

# Ingest the env variables to any pod in airflow namespace
env:
  - name: AIRFLOW__LOGGING__REMOTE_LOGGING
    value: "True"
  - name: AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER
    value: "s3://airflow-logs"
  - name: AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID
    value: "minio_conn"
  - name: AIRFLOW__LOGGING__ENCRYPT_S3_LOGS
    value: "False"
  - name: AWS_ACCESS_KEY_ID
    value: minioadmin
  - name: AWS_SECRET_ACCESS_KEY
    value: minioadmin
  - name: AWS_ENDPOINT_URL
    value: http://minio:9000
  - name: AWS_DEFAULT_REGION
    value: us-east-1
```

## Installing Apache Spark on Kubernetes
```bash
kubectl create ns spark-operator
kubectl apply -f spark-rbac.yaml
helm upgrade --install spark-operator spark-operator/spark-operator --namespace spark-operator -f values.yaml
```

## Installing jupyter-pyspark on Kubernetes
```bash
kubectl create ns jupyter-pyspark
kubectl apply -f pvc-pyspark.yaml
kubectl apply -f jupyter-pyspark.yaml
```

## Installing Strimzi Kafka(KRaft Mode) on Kubernetes

```bash
# Add helm repo
helm repo add strimzi https://strimzi.io/charts/
helm repo update

# Create namespace
kubectl create namespace kafka

# Export value from helm and overwrite the default image
helm show values bitnami/kafka > values-examples.yaml

# Install Kafka operator using Helm
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  -n kafka \
  --set watchNamespaces={kafka}

# Install Kafka cluster -> controller -> broker
kubectl apply -f kafka-cluster.yaml
kubectl apply -f kafka-controller.yaml
kubectl apply -f kafka-broker.yaml

```









load local docker image into Minikube:


5. Deploy Metabase with PostgreSQL as metadata
  1. create metabase namespace
  2. create helm chart
  3. install chart
  ```bash
  helm upgrade --install metabase ./metabase -n metabase
  ```
  4. Check status
  ```bash
  kubectl get pods -n metabase
  kubectl get svc -n metabase
  ```
  5. Access Metabase (port-forward)

  6. add ClickHouse database
    1. login clickhouse
    ```bash
    kubectl exec -it -n clickhouse-operator chi-analytics-ch-analytics-0-0-0 -- clickhouse-client
    ```

    创建 Metabase 用户（推荐 SQL）
    ```sql
    CREATE USER IF NOT EXISTS metabase
    IDENTIFIED WITH sha256_password BY 'metabase_password'
    HOST ANY;
    ```



Helm 渲染检查
```bash
helm template metabase ./metabase-chart -n metabase | grep image:
```

  get service name of ClickHouse:
  ```bash
  kubectl get svc -n clickhouse-operator
  ```




6. install ClickHouse using Helm

推荐 Altinity 官方 Chart（最稳定、最常用）
```bash
helm repo add altinity https://altinity.github.io/clickhouse-operator/
helm repo update
```

安装clickhouse-operator 
```bash
helm install clickhouse-operator altinity/altinity-clickhouse-operator \
  --namespace clickhouse-operator \
  --create-namespace
```

安装ClickHouse
```bash
helm install clickhouse altinity/clickhouse \
  --namespace clickhouse \
  --create-namespace \
  -f values.yaml
```

Validation
```bash
kubectl get pods -n clickhouse-operator
kubectl get crd | grep clickhouse
```

部署 ClickHouse Keeper（生产关键）

Create keeper.yaml
```YAML
# keeper.yaml
```
Apply the config
```bash
kubectl apply -f keeper.yaml
```

定义 ClickHouse 多副本集群（核心）
```YAML
# chi.yaml
```

进入任意一个ClickHouse Pod:
```bash
kubectl exec -it -n clickhouse-operator \
  chi-analytics-ch-analytics-0-0-0 \
  -- clickhouse-client
```


## Appendix
k9s tips:

filter component: :command,  :ns :deploy :svc etc
enter the shell for the slected pod: enter `s`
exited the pod : `ctrl + D`
port forward: `shift + f`

常见快捷方式：
| 快捷键 | 作用         |
| --- | ---------- |
| `s` | 进入 shell   |
| `c` | 查看 Pod 内容器 |
| `l` | 查看 logs    |
| `d` | describe   |
| `e` | edit YAML  |
| `x` | delete     |
| `:` | 命令模式       |

常用滚动快捷键汇总（在 Describe / Logs / YAML 视图中）
| 快捷键                   | 作用                    |
| --------------------- | --------------------- |
| `G`                   | 跳到最后                  |
| `g`                   | 跳到第一行                 |
| `Ctrl + d`            | 向下滚动半页                |
| `Ctrl + u`            | 向上滚动半页                |
| `PageDown` / `PageUp` | 翻页                    |
| `/`                   | 搜索（回车后用 `n` / `N` 跳转） |
| `q` / `Esc`           | 退出当前视图                |


enter the docker inside minikube:
```bash
eval $(minikube docker-env)
```

```bash
minikube image load metabase/metabase:latest
```


## Architecture

![architecture.png](./airflow3-on-K8s.png)

## Disclaimer

Not production ready code - gives the reader a rough idea on how to deploy your own data platform.

Recommended to add more production ready features, such as running this on AWS EKS (Elastic Kubernetes Service), using S3 Remote for logging, replacing Airflow's Postgres instance with own Postgres server, keeping secrets in something like Vault or secrets manager and much more.



port:
8080 - Airflow
9001 - MinIO
     - Spark UI
8888 - Jupyter Notebook


3000 - Grafana