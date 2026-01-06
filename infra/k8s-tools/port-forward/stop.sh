#!/usr/bin/env bash

PID_DIR="$(dirname "$0")/pids"

echo "🛑 Stopping all port-forwards..."

for pid in "$PID_DIR"/*.pid; do
  [[ -f "$pid" ]] || continue
  kill "$(cat "$pid")" 2>/dev/null || true
  rm -f "$pid"
done

echo "✅ All port-forwards stopped"
