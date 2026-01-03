# k3s Single-Node Base Configuration (Practical Guide)

> **Goal**: Stability, observability, scalability, and zero data loss

---

## 0. Install k3s

```bash
curl -sfL https://get.k3s.io | sh -
```

## 1. k3s Startup Parameters

```bash
sudo systemctl stop k3s

sudo k3s server \
  --disable servicelb \
  --disable traefik \
  --write-kubeconfig-mode 644 

sudo systemctl start k3s
```

## 2. Configure kubeconfig
```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
```


## 3. Logging & Observability

Install Metrics Server:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```
Verification:
  View node and pod metrics:
  ```bash
  kubectl top node
  kubectl top pod -A
  ```
## 4. Using `crictl`
```bash
kubectl get pod -A
sudo crictl ps
```

卸载 K3s：
在你的服务器上运行以下命令来卸载 K3s：

sudo /usr/local/bin/k3s-uninstall.sh
这将卸载 K3s 并删除与 K3s 相关的所有文件和服务。


清理 K3s 配置和数据：
如果你希望彻底清理，可以删除 K3s 配置文件和数据目录：

sudo rm -rf /etc/rancher/k3s
sudo rm -rf /var/lib/rancher/k3s
sudo rm -rf /var/log/k3s