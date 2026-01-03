安装 kube-prometheus-stack
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

```bash
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n prometheus \
  --create-namespace
```

检查安装状态：
`kubectl --namespace prometheus get pods -l "release=prometheus"`

获取 Grafana 密码(账号admin)
`kubectl get secret -n prometheus prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo`
5AVWqpTRFiGqOlPnPTpfcEd7jwF8kFAQvviCWEYm

端口转发
`kubectl port-forward -n prometheus svc/prometheus-grafana 3000:80`