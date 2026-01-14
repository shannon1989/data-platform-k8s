## Dagster repository

Create repository.py
```python
from dagster import Definitions

from assets_backfill import eth_block_backfill

defs = Definitions(
    assets=[eth_block_backfill],
)
```

## Minikube build image:
```bash
eval $(minikube docker-env)
docker build -t eth-dagster-user-code:0.1.0 .
```

## Create user code deloyement with helm

```bash
# install or upgrade
helm upgrade --install user-code dagster/dagster-user-deployments -f dagster-user-deployment.yaml -n dagster
# uninstall
helm uninstall user-code -n dagster
```

### run config in materizlized asset
```YAML
ops:
  eth_block_backfill:
    config:
      start_date: "2026-01-02"
      end_date: "2026-01-03"
```

```bash
kubectl apply -f dagster-instance.yaml
kubectl rollout restart deployment dagster-daemon -n dagster
kubectl rollout restart deployment dagster-dagster-webserver -n dagster
```

