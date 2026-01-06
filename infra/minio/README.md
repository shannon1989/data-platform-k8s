## 3. MinIO Deployment:

```bash
kubectl create ns airflow
```

```bash
kubectl apply -f .
```
Port-forward and access MinIO Web Console: (user: minioadmin pass: minioadmin)
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

Airflow configuration with MinIO Connection (after airflow is deployed)
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