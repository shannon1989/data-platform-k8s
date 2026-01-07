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

register blockchain.blocks-key blockchain.blocks.key.avsc
register blockchain.blocks-value blockchain.blocks.value.avsc
register blockchain.ingestion_state-key blockchain.ingestion_state.key.avsc
register blockchain.ingestion_state-value blockchain.ingestion_state.value.avsc
