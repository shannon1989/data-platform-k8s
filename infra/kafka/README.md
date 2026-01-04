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

# redpand install
add helm repo
```bash
helm repo add redpanda https://charts.redpanda.com
helm repo update
```

```bash
helm install redpanda-console redpanda/console \
  -n kafka \
  -f values.yaml
```