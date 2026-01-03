# k3s 单机「生产级」基础配置清单（实战版）
> 目标：稳、可观测、可扩展、数据不丢

https://blog.offends.cn/Kubernetes/%E9%83%A8%E7%BD%B2%E6%96%87%E6%A1%A3/Rancher-K3s/K3s%E9%83%A8%E7%BD%B2%E7%A6%81%E7%94%A8%E8%87%AA%E5%B8%A6%E9%99%84%E5%8A%A0%E7%BB%84%E4%BB%B6.html

0. 安装k3s:
    `curl -sfL https://get.k3s.io | sh -`

1. K3s 启动参数
```bash
sudo systemctl stop k3s
sudo k3s server --disable servicelb --write-kubeconfig-mode 644 --kube-apiserver-arg=feature-gates=EphemeralContainers=true
sudo systemctl start k3s
```

2. 配置kubeconfig
```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
```

2. Node 级别资源保留（防止系统被吃死）
    - 设置 kubelet 资源预留
      - `sudo vim /etc/systemd/system/k3s.service`
    - 找到 ExecStart，追加：(👉 对 Spark + Kafka + ClickHouse 非常关键)
      ```bash
      --kubelet-arg=system-reserved=cpu=500m,memory=1Gi \
      --kubelet-arg=kube-reserved=cpu=500m,memory=1Gi \
      --kubelet-arg=eviction-hard=memory.available<500Mi
      ```
3. HostPath 目录结构（重中之重）强烈推荐统一在一个根目录 (👉 这是你未来迁移到云的“数据边界”)
    - `sudo mkdir -p /data/{airflow,logs,minio,kafka,clickhouse,spark}`
    - `sudo chown -R 1000:1000 /data`

4. StorageClass(统一 HostPath 策略)
```bash
kubectl apply -f local-path-sc.yaml
```

5. Container Runtime & IO 优化 - （Kafka / Airflow 需要）
```bash
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
echo fs.inotify.max_user_instances=8192 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```
6. 日志与观测
    - `kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml`

    验证:
      - `kubectl top node`
      - `kubectl top pod -A`

8. 安全 & 权限（别踩坑）关闭 swap（必须）
```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```
9. 安全 & 权限 - App 尽量不用 root - 在 Helm values 里:
```YAML
securityContext:
  runAsUser: 1000
  fsGroup: 1000
```

10. Airflow / Spark Operator 的 k3s 特别注意点
- Airflow
    - Executor：KubernetesExecutor / K8sPodOperator
    - Logs：MinIO
    - 不用 NodePort

- Spark Operator
    - spark.local.dir=/data/spark
    - executor memory 要算上 system-reserved

11. 使用crictl
```bash
kubectl get pod -A
sudo crictl ps
```