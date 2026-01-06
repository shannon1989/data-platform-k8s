#!/usr/bin/env bash
set -e

PID_DIR="$(dirname "$0")/.pids"
mkdir -p "$PID_DIR"

echo "🚀 Starting port-forward services..."

port_forward() {
  local name=$1
  local namespace=$2
  local resource=$3
  local mapping=$4

  local pid_file="$PID_DIR/$name.pid"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "⚠️  $name already running"
    return
  fi

  echo "➡️  $name : localhost:${mapping%%:*} → $namespace/$resource:${mapping##*:}"

  kubectl port-forward -n "$namespace" "$resource" "$mapping" \
    >"$PID_DIR/$name.log" 2>&1 &

  echo $! > "$pid_file"
}

# ===== define all ports =====

# Monitoring
port_forward kubernetes-dashboard kubernetes-dashboard svc/kubernetes-dashboard 9090:9090
port_forward headlamp kube-system svc/kube-system 4466:4466
port_forward prometheus prometheus svc/prometheus-kube-prometheus-prometheus 3000:9090
port_forward grafana prometheus svc/prometheus-grafana 3001:80

# Minio
port_forward minio airflow svc/minio 9001:9001

# Orchestration
port_forward airflow airflow svc/airflow-api-server 8081:8080
port_forward dagster dagster svc/dagster-webserver 3003:80

# Kafka
port_forward redpanda kafka svc/redpanda-console-console 3004:8080

# Jupyter Pyspark
port_forward jupyter jupyter-pyspark svc/jupyter-pyspark 8888:8888

echo "✅ All port-forwards started"
echo "📂 Logs & PIDs in ./pids/"