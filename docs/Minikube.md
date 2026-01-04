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
