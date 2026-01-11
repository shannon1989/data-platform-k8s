## Installing jupyter-pyspark on Kubernetes

pull image
```bash
docker pull quay.io/jupyter/pyspark-notebook:python-3.11
```

build custom image
```bash
eval $(minikube docker-env) # for minikube only
docker build -t jupyter-pyspark:0.1.2 .
```

```bash
kubectl create ns jupyter-pyspark
kubectl apply -f jupyter-pvc.yaml
kubectl apply -f jupyter-pyspark.yaml
```