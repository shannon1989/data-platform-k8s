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


register blockchain.ingestion.bsc.mainnet.logs-key blockchain.ingestion.bsc.mainnet.logs-key.avsc
register blockchain.ingestion.bsc.mainnet.logs-value blockchain.ingestion.bsc.mainnet.logs-value.avsc
register blockchain.ingestion.bsc.mainnet.state-key blockchain.ingestion.bsc.mainnet.state-key.avsc
register blockchain.ingestion.bsc.mainnet.state-value blockchain.ingestion.bsc.mainnet.state-value.avsc