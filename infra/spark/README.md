## Installing Apache Spark on Kubernetes
```bash
kubectl create ns spark-operator
kubectl apply -f spark-rbac.yaml
helm upgrade --install spark-operator spark-operator/spark-operator --namespace spark-operator -f values.yaml
```