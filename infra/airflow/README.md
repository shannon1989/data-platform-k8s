## 2. Airflow 3.0 deployement
Create Airflow namespace
```bash
kubectl create ns airflow
```

Create SSH Key Secret for Git Access
```bash
ssh-keygen -t rsa -b 4096 -C "example@gmail.com" -f ./airflow_gitsync_id_rsa
```

Create a Kubernetes secret on airflow namespace from the private key
```bash
kubectl create secret generic airflow-git-ssh-key-secret \
--from-file=gitSshKey=./airflow_gitsync_id_rsa \
--namespace airflow 
--dry-run=client -o yaml > airflow-git-ssh-key-secret.yaml
```

Apply the secret to the Kubernetes cluster
```bash
kubectl apply -f airflow-git-ssh-key-secret.yaml
kubectl apply -f airflow-postgresql-credentials-secret.yaml
```
Add Deploy Key to Git Repository

> Copy the contents of airflow_gitsync_id_rsa.pub and add it as a Deploy Key with read-only access in your Git repository. [GitHub Deploy Key Docs](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys#deploy-keys)

Deploy Airflow
```bash
helm -n airflow upgrade --install airflow apache-airflow/airflow -f values.yaml
```

Port-forward and access Airflow Web Console: [http://localhost:8080](http://localhost:8080) (user: admin pass: admin)
```bash
kubectl -n airflow port-forward svc/airflow-api-server 8080:8080
```