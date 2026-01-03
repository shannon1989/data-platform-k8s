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

## 4. Install Kafka cluster -> controller -> broker
```bash
kubectl apply -f kafka-cluster.yaml
kubectl apply -f kafka-controller.yaml
kubectl apply -f kafka-broker.yaml
```