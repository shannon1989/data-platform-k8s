# Copilot instructions for data-platform-k8s

Brief, actionable guidance to help an AI coding agent be productive in this repository.

## Big picture (what this repo is)
- Kubernetes-based data platform integrating: **Airflow** (KubernetesExecutor), **Spark (Spark Operator)**, **Kafka (Strimzi)**, **MinIO** (S3), **Metabase**, and **Jupyter**. See top-level `README.md` and `docs/README.md` for architecture diagrams and goals.

## Where to look first (key files & directories)
- Deployment & configuration: `apps/` — contains per-component YAMLs and Helm values (e.g., `apps/airflow/helm-values.yaml`, `apps/spark/`, `apps/kafka/`, `apps/minio/`).
- Examples & runnable jobs: `examples/` (e.g., `examples/dags-local/hello_world_dag.py`, `examples/dags-local/spark-apps/spark-pi.yaml`). Use these to run smoke tests.
- Container images: `images/` (e.g., `images/spark/Dockerfile.spark`, `images/jupyter-pyspark/Dockerfile`). Build & load into Minikube for local testing.
- Docs and runbooks: `docs/` (deploy steps for Minikube, k3s tips, Helm commands). Treat these as the authoritative operational steps.
- Secrets & deploy keys: `secret/` contains example SSH keys and k8s secret YAMLs used by Airflow GitSync.

## Developer workflows to reference or use (concrete commands)
- Start local cluster: `minikube start --cpus=8 --memory=16g` (see `docs/README.md`). For k3s use `docs/k3s.md`.
- Build/load images locally for Minikube:
  - `eval $(minikube docker-env)` then `docker build -t <name>:<tag> .` or `minikube image load <image>`
- Install Airflow (example):
  - `kubectl create ns airflow`
  - Create SSH deploy key and k8s secret (see `docs/README.md` and `apps/airflow/helm-values.yaml`).
  - `helm -n airflow upgrade --install airflow apache-airflow/airflow -f values.yaml`
  - Port-forward web UI: `kubectl -n airflow port-forward svc/airflow-api-server 8080:8080`
- Install Spark operator: `helm upgrade --install spark-operator spark-operator/spark-operator --namespace spark-operator -f values.yaml`
- Kafka (Strimzi) and ClickHouse steps are in `docs/README.md` (helm/manifest-based installs).
- Configure MinIO for Airflow remote logs: create bucket + Airflow connection (examples in `docs/README.md`).

## Project-specific conventions & patterns
- Airflow uses GitSync to pull DAGs from a repo via SSH (see `apps/airflow/helm-values.yaml`): ensure deploy key in `secret/` or add a real Deploy Key to your Git repository.
- Use Helm where possible (charts under `apps/` and `metabase-chart/`), otherwise apply raw k8s manifests from `apps/*`.
- Namespaces are explicit: common namespaces include `airflow`, `spark-operator`, `kafka`, `metabase`, `jupyter-pyspark`.
- Spark jobs should be submitted via Spark Operator CRDs (see `apps/spark/` configs and `examples/spark-apps/spark-pi.yaml`).

## Integration / dependency notes
- Airflow -> Spark: tasks are expected to create SparkApplications (client or cluster mode) using KubernetesExecutor.
- Airflow remote logs and many example DAGs rely on MinIO; credentials are injected via env vars in `apps/airflow/helm-values.yaml`.
- Kafka is installed via Strimzi manifests/Helm; verify namespaces & CRDs when working with Kafka topics.

## Helpful quick examples to reference
- Example DAG: `examples/dags-local/hello_world_dag.py` (shows basic DAG layout used across repo).
- Spark example: `examples/dags-local/spark-apps/spark-pi.yaml` (useful when testing Spark Operator installs).
- Airflow GitSync config: `apps/airflow/helm-values.yaml` (shows SSH key secret name and known_hosts entry).

## What an agent should *not* assume
- There are no automated unit/integration tests in repo root — do not assume CI exists for code changes.
- Secrets in `secret/` are example/test material; do not assume they are production-ready.

## Suggested prompts for the agent
- "Open `apps/airflow/helm-values.yaml` and update the Git repo URL and known_hosts entry to match the provided deploy key; show the exact `kubectl` commands to apply the secret and re-deploy Airflow." 
- "Add a smoke test DAG under `examples/dags-local/` that asserts a Spark job can be submitted to the Spark Operator and completes within N minutes. Use existing spark-pi YAML as reference."

---
If anything here is unclear or you'd like me to expand with CI steps, example PRs, or automated smoke-tests, tell me which area to focus on and I’ll iterate. ✅
