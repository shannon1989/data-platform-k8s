# Install and deploy Dagster

## Introduction
  - 使用 Postgres（不是 sqlite）
  - 使用 K8sRunLauncher（每个 run 一个 Pod）
  - user code 单独部署（后面用）

Architecture
```TEXT
┌──────────────────────────────┐
│          Dagster UI          │  WebServer
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│        Dagster Daemon        │  Scheduler / Sensor / Asset
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│        Dagster gRPC          │  (user code)
│   (pipelines live here)  │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│      Postgres (Metadata)     │
└──────────────────────────────┘
```

## 1. Create namespace
```bash
kubectl create namespace dagster
```

## 2. Add Helm Repo
```bash
helm repo add dagster https://dagster-io.github.io/helm
helm repo update
```

## 3. Install Dagster without example code
and Separately deploying Dagster infrastructure and user code

```bash
helm install dagster dagster/dagster -n dagster -f values.yaml
```
### show default values.yaml
```bash
helm show values dagster/dagster > values-examples.yaml
```

### port-forward
```bash
kubectl port-forward svc/dagster-dagster-webserver 3001:80 -n dagster
```
### Access
http://localhost:3001

### Official doc:
https://docs.dagster.io/deployment/oss/deployment-options/kubernetes/customizing-your-deployment