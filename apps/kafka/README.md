## Installing Strimzi Kafka(KRaft Mode) on Kubernetes

```bash
# Add helm repo
helm repo add strimzi https://strimzi.io/charts/
helm repo update

# Create namespace
kubectl create namespace kafka

# Export value from helm and overwrite the default image
helm show values bitnami/kafka > values-examples.yaml

# Install Kafka operator using Helm
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  -n kafka \
  --set watchNamespaces={kafka}

# Install Kafka cluster -> controller -> broker
kubectl apply -f kafka-cluster.yaml
kubectl apply -f kafka-controller.yaml
kubectl apply -f kafka-broker.yaml

```
