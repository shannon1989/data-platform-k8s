## start with cpus and memory config
minikube start --cpus=8 memory=16g


## config cpus and memory
minikube stop
minikube config set cpus 6
minikube config set memory 16384
minikube start

## start metrics server:
```bash
minikube addons enable metrics-server
```

## Check current config
minikube config view

## Headlamp 

### Add repo
helm repo add headlamp https://kubernetes-sigs.github.io/headlamp/
helm repo update

### Install
```bash
helm upgrade --install headlamp headlamp/headlamp \
 -n kube-system \
 --set clusterRoleBinding.create=true \
 --set kubeconfig.enabled=false
```

Start Cluster Admin (Dev environment):
```bash
helm upgrade --install headlamp headlamp/headlamp \
  -n kube-system \
  --set clusterRoleBinding.create=true \
  --set clusterRoleBinding.name=headlamp-admin
```

get the token:
```bash
kubectl create token headlamp --namespace kube-system
```

check the log
```bash
kubectl logs -n kube-system deploy/headlamp
```


## Ingress Setting
minikube ip

minikube addons enable ingress

✅ 1️⃣ 用 minikube stop 而不是关机（强烈建议）
minikube stop
# 第二天
minikube start

✅ 2️⃣ 不用就 pause（最快）
minikube pause
# 恢复
minikube unpause
