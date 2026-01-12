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

register blockchain.logs.bsc-key blockchain.logs.bsc-key.avsc
register blockchain.logs.bsc-value blockchain.logs.bsc-value.avsc
register blockchain.state.bsc-key blockchain.state.bsc-key.avsc
register blockchain.state.bsc-value blockchain.state.bsc-value.avsc
