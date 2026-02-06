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

# state
register blockchain.ingestion._state-key ingestion._state-key.avsc
register blockchain.ingestion._state-value ingestion._state-value.avsc

# blocks
register blockchain.bsc.ingestion.blocks.raw-key bsc.ingestion.blocks.raw-key.avsc
register blockchain.bsc.ingestion.blocks.raw-value bsc.ingestion.blocks.raw-value.avsc

# transactions
register blockchain.bsc.ingestion.transactions.raw-key bsc.ingestion.transactions.raw-key.avsc
register blockchain.bsc.ingestion.transactions.raw-value bsc.ingestion.transactions.raw-value.avsc

# logs
register blockchain.bsc.ingestion.logs.raw-key bsc.ingestion.logs.raw-key.avsc
register blockchain.bsc.ingestion.logs.raw-value bsc.ingestion.logs.raw-value.avsc