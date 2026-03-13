## install k3s on ubuntu
```bash
curl -sfL https://get.k3s.io | sh -
```

## install k3s without Traefik
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
