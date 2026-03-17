## Step 1
kubectl create ns compute
create airflow-logs bucket

## Setp 2
```bash
kubectl create secret generic r2-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=<R2_ACCESS_KEY> \
  --from-literal=secreAWS_SECRET_ACCESS_KEYtkey=<R2_SECRET_KEY> \
  -n compute
```

## step 3 - create airflow-postgresql-credentials.yaml

## step 4 - create helm-values.yaml

## step 5 - Install Airflow
```bash
helm repo add apache-airflow https://airflow.apache.org/
helm repo update

helm -n compute upgrade --install airflow apache-airflow/airflow -f helm-values.yaml
```

## step 6 - Airflow UI connection setup
- add connection from Airflow UI -> Admin -> Connections
  - Extra Fields -> In cluster configuration (True)

| 字段        | 填写示例                                                                                                             | 说明                                       |
| --------- | --------------------- | --------------------- |
| Conn Id   | `r2_conn` | 你 Helm values 里 `remote_log_conn_id` 要一致 |
| Conn Type | AWS ->`S3`  | Cloudflare R2 支持 S3 API                  |
| Login     | `<R2_ACCESS_KEY>`  | R2 的 Access Key                          |
| Password  | `<R2_SECRET_KEY>` | R2 的 Secret Key                          |
| Extra     | `json {"host":"https://<ACCOUNT_ID>.r2.cloudflarestorage.com","region_name":"auto","signature_version":"s3v4"} ` | JSON 格式，指定 R2 endpoint、region、签名方式       |

## step 7 - dag testing
# 假设你在本地把 DAG 文件放到 dags 目录
kubectl -n compute cp test_r2_log_dag.py <webserver-pod>:/opt/airflow/dags/

## step 6 - check images
```bash
sudo crictl images
```