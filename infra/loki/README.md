helm upgrade loki grafana/loki-stack \
  --namespace prometheus \
  -f loki-values.yaml

helm upgrade loki grafana/loki-stack \
  --namespace prometheus \
  --set promtail.securityContext.runAsUser=0 \
  --set promtail.securityContext.runAsGroup=0 \
  -f loki-values.yaml