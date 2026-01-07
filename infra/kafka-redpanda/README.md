# Production ready RedPanda helm install
- ✅ Production baseline
- ✅ 3 Broker
- ✅ Schema Registry
- ✅ Redpanda Console（Web UI）
- ✅ StatefulSet + PVC
- ❌ no TLS / SASL（can be upgraded）

helm repo add redpanda https://charts.redpanda.com
helm repo update

dry-run:
```bash
helm install redpanda redpanda/redpanda \
  -n kafka \
  -f redpanda-values.yaml \
  --dry-run=client
```

install
```bash
helm upgrade --install redpanda redpanda/redpanda \
  -n kafka \
  -f redpanda-values.yaml
```