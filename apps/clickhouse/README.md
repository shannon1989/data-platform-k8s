# ClickHouse deployement and Prometheus config
  
## Install ClickHouse using Helm

| 组件                            | 作用       |
| ----------------------------- | -------- |
| ClickHouse Operator           | 管理集群生命周期 |
| ClickHouseInstallation (CHI)  | 声明式定义集群  |
| Zookeeper / ClickHouse Keeper | 元数据 & 复制 |
| ReplicatedMergeTree           | 高可用表引擎   |


1. Using Altinity official Chart
```bash
helm repo add altinity https://altinity.github.io/clickhouse-operator/
helm repo update
```

2. install clickhouse-operator 
```bash
helm install clickhouse-operator altinity/altinity-clickhouse-operator \
  --namespace clickhouse \
  --create-namespace


4. 定义 ClickHouse 单副本集群
```YAML
# chi.yaml
```

验证分片(shards):

进入任意一个ClickHouse Pod:
```bash
kubectl exec -it -n clickhouse-operator chi-analytics-ch-analytics-0-0-0 -- clickhouse-client
```


Clickhouse分区验证：
```sql
CREATE DATABASE IF NOT EXISTS analytics
ON CLUSTER analytics;
```

## install ss, ping, nc
apt-get update && \
apt-get install -y iproute2 iputils-ping netcat-openbsd

root@chi-analytics-ch-analytics-1-0-0:/# ss -lntp | grep 9000
LISTEN   0        4096                   *:9000                *:*

root@chi-analytics-ch-analytics-1-0-0:/# ping -c 2 chi-analytics-ch-analytics-0-0
PING chi-analytics-ch-analytics-0-0 (198.18.0.64) 56(84) bytes of data.
64 bytes from 198.18.0.64 (198.18.0.64): icmp_seq=1 ttl=62 time=0.316 ms
64 bytes from 198.18.0.64 (198.18.0.64): icmp_seq=2 ttl=62 time=0.326 ms

--- chi-analytics-ch-analytics-0-0 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1003ms
rtt min/avg/max/mdev = 0.316/0.321/0.326/0.005 ms

root@chi-analytics-ch-analytics-1-0-0:/# nc -vz chi-analytics-ch-analytics-0-0 9000
Connection to chi-analytics-ch-analytics-0-0 9000 port [tcp/*] succeeded!