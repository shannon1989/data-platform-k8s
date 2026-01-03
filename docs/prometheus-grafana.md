## Install kube-prometheus-stack

Create namespace
```bash
kubectl create ns prometheus
```

Add repo
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

!Default values for Grafana Readiness: (failed in 30 seconds before all containers inside the pod are ready )
`delay=0s timeout=1s period=10s #success=1 #failure=3`
new value:
```YAML
grafana:
  readinessProbe:
    httpGet:
      path: /api/health
      port: grafana
    initialDelaySeconds: 30
    timeoutSeconds: 10
    failureThreshold: 5
```


Install prometheus/Grafana
```bash
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack -n prometheus 
```

Get your grafana admin user password
```bash
kubectl get secret -n prometheus prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
```

Port-forward
```bash
kubectl port-forward -n prometheus svc/prometheus-grafana 3000:3000
```

Add Prometheus data source in Grafana:
Get service IP from service prometheus-kube-prometheus-prometheus