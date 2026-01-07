# Installing Strimzi Kafka(KRaft Mode) on Kubernetes


## 1. Create namespace
```bash
kubectl create namespace kafka
```

## 1. Add helm repo
```bash
helm repo add strimzi https://strimzi.io/charts/
helm repo update
```
## 2. Install Kafka operator using Helm
```bash
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  -n kafka \
  --set watchNamespaces={kafka}
```

## 3. Define broker, cluster and controller.
  - kafka-cluster.yaml
  - kafka-controller.yaml
  - kafka-broker.yaml

## 4. Install Kafka cluster, controller, broker
```bash
kubectl apply -f .
```

How to fix "Exception in thread "main" java.lang.RuntimeException: Invalid cluster.id in: /var/lib/kafka/data/kafka-log0/meta.properties. Expected jtBtuYymS9WguHKEZrNywQ, but read zDoptgm6RsSqjOYI7tkJYQ"

```YAML
apiVersion: kafka.strimzi.io/v1
kind: Kafka
metadata:
  name: kafka
  namespace: kafka
  annotations:
    strimzi.io/cluster-id: zDoptgm6RsSqjOYI7tkJYQ 
```