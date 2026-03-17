## 系统级前置优化

**Fail2ban**
```bash
# install
sudo apt install fail2ban -y
# start
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

**k8s preparation**
```bash
# chrony
sudo apt install chrony -y
# close swap
sudo swapoff -a
sudo sed -i '/swap/d' /etc/fstab

# kernel parameter
sudo tee /etc/sysctl.d/k8s.conf <<EOF
vm.max_map_count=262144
fs.file-max=1000000
net.core.somaxconn=65535
EOF
# load
sudo sysctl --system
```

**br_netfilter**
```bash
sudo modprobe br_netfilter
echo br_netfilter | sudo tee /etc/modules-load.d/k8s.conf
```

## install k3s without Traefik (use ingress-nginx)
```bash
curl -sfL https://get.k3s.io | sh -s - --disable traefik
```

## check status
```bash
sudo systemctl status k3s
sudo k3s kubectl get nodes
```

## 设置 kubectl（推荐）
```bash
# update privilege
sudo chmod 644 /etc/rancher/k3s/k3s.yaml

mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
```

## install helm
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

## install Nginx Ingress
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

## install Longhorn (storage layer)

PVC管理更稳定
快照
备份
卷恢复
可视化

```bash
helm repo add longhorn https://charts.longhorn.io
helm repo update

helm install longhorn longhorn/longhorn \
  -n longhorn-system \
  --create-namespace

# update Longhorn default folder
kubectl edit settings.longhorn.io default-data-path -n longhorn-system
/data/longhorn
```

## create directory
```bash
sudo mkdir -p /data/k8s
sudo mkdir -p /data/longhorn
sudo chmod -R 777 /data
```

## create namespace
```bash
# infra - kafka/clickhouse
kubectl create ns infra

# compute - spark/flink/airflow
kubectl create ns compute

# analytics - metabase/trino
kubectl create ns analytics

# monitoring - prometheus/grafana
kubectl create ns monitoring

# logging -> Elasticsearch / Logstash / Kibana / Beats
kubectl create ns logging

# jupyter
kubectl create ns dev
```

## install kube-prometheus-stack
```bash
# add helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# install prometheus and grafana (optimized for server with 2G memory)
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n prometheus \
  --create-namespace \
  -f prometheus-values.yaml
```
