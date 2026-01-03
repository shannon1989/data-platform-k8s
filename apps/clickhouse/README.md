# ClickHouse non-HA deployement and Prometheus config
  

## 1. Create clickhouse namespace
```bash
kubectl create ns clickhouse
```

## 2. Add repo from Altinity official Chart
```bash
helm repo add altinity https://altinity.github.io/clickhouse-operator/
helm repo update
```

## 3. install clickhouse-operator 
```bash
helm install clickhouse-operator altinity/altinity-clickhouse-operator -n clickhouse
```

## 4. Defin ClickHouse single shard cluster
```TEXT
keeper.yaml
chi.yaml
```

**How to install ss, ping, nc inside POD:**
apt-get update && \
apt-get install -y iproute2 iputils-ping netcat-openbsd
