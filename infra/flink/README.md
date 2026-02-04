download: https://downloads.apache.org/flink/flink-kubernetes-operator-1.13.0/

kubectl create namespace flink


helm install flink-kubernetes-operator \
  ./flink-kubernetes-operator-1.13.0-helm.tgz \
  -n flink

