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
  --write-kubeconfig-mode 644 \
  --kube-apiserver-arg=feature-gates=EphemeralContainers=true

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
  - View node metrics:
    ```bash
    kubectl top node
    ```
  - View pod metrics:
    ```bash
    kubectl top pod -A
    ```
## 4. Using `crictl`
```bash
kubectl get pod -A
sudo crictl ps
```