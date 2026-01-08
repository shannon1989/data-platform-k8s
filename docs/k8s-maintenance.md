delete namespace in "Terminating" status

```bash
# template
kubectl get ns <ns-name> -o json \
| jq '.spec.finalizers=[] | .metadata.finalizers=[]' \
| kubectl replace --raw "/api/v1/namespaces/<ns-name>/finalize" -f -
```

```bash
# confluent namespace
kubectl get ns confluent -o json \
| jq '.spec.finalizers=[] | .metadata.finalizers=[]' \
| kubectl replace --raw "/api/v1/namespaces/confluent/finalize" -f -
```