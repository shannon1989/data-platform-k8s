## Installing jupyter-pyspark on Kubernetes
```bash
kubectl create ns jupyter-pyspark
kubectl apply -f pvc-pyspark.yaml
kubectl apply -f jupyter-pyspark.yaml
```