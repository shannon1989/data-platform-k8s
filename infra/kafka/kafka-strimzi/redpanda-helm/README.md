## redpand install - UI with schema regirstry config
add helm repo
```bash
helm repo add redpanda https://charts.redpanda.com
helm repo update
```

```bash
helm upgrade --install redpanda-console redpanda/console \
  -n kafka \
  -f values-console.yaml
```