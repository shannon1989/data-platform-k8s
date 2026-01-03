## 安装官方 local-path-provisioner

kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml

这一步会创建：

- Namespace: local-path-storage
- Deployment: local-path-provisioner
- StorageClass: local-path（默认）