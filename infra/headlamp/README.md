## first add our custom repo to your local helm repositories
helm repo add headlamp https://kubernetes-sigs.github.io/headlamp/
helm repo update

# now you should be able to install headlamp via helm
helm install headlamp headlamp/headlamp -n kube-system -f headlamp-values.yaml

# Get the token
kubectl create token headlamp --namespace kube-system


Headlamp supported mode:

| Mode                | function           |
| ------------------ | ------------- |
| kubeconfig file      | local       |
| Dynamic kubeconfig | multi-node           |
| InCluster | insdie k8s |