# Install and config Promethues/Grafana

## 1. Create prometheus namespace
```bash
kubectl create ns prometheus
```

## 2. Add repo from kube-prometheus-stack
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```
## 3. update default values from chart (k3s cluster only)
  !Default values for Grafana Readiness: (failed in 30 seconds before all containers inside the pod are ready )
  `delay=0s timeout=1s period=10s #success=1 #failure=3`
```YAML
grafana:
  readinessProbe:
    httpGet:
      path: /api/health
      port: grafana
    initialDelaySeconds: 30 # Wait longer before starting checks
    timeoutSeconds: 10
    failureThreshold: 5

  sidecar:
    datasources:
      enabled: true
      defaultDatasourceEnabled: false # Do not create Prometheus datasource by default
```

## 4. Install prometheus with customed value
```bash
helm install prometheus prometheus-community/kube-prometheus-stack -n prometheus -f values.yaml
```

## 5. Get your grafana admin user password
```bash
kubectl get secret -n prometheus prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
```

## 6. Port forward (minikube only)
```bash
kubectl port-forward -n prometheus svc/prometheus-grafana 3000:80
```

## How to restart statefulSet
```bash
kubectl rollout restart statefulset prometheus-prometheus-kube-prometheus-prometheus -n prometheus
```
## How to restart deployment
```bash
kubectl rollout restart deployment prometheus-kube-state-metrics -n prometheus
```