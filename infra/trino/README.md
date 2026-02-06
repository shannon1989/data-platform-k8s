helm repo add trino https://trinodb.github.io/charts
helm repo update


helm install trino trino/trino \
  -n trino \
  --create-namespace \
  -f values-trino.yaml
