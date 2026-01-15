#!/usr/bin/env bash
set -e

REGISTRY_URL="http://localhost:18081" # schema registry port

register () {
  local subject=$1
  local file=$2

  echo "Registering $subject from $file"

  curl -s -X POST \
    "${REGISTRY_URL}/subjects/${subject}/versions" \
    -H "Content-Type: application/vnd.schemaregistry.v1+json" \
    -d "$(jq -n --arg schema "$(cat "$file")" '{schema: $schema}')" \
  | jq
}

register blockchain.logs.base-key blockchain.logs.base-key.avsc
register blockchain.logs.base-value blockchain.logs.base-value.avsc
register blockchain.state.base-key blockchain.state.base-key.avsc
register blockchain.state.base-value blockchain.state.base-value.avsc
