# Blockchain Ingestion Specification (Avro-based)

## 1. Background

This document defines a **generic, extensible ingestion schema** for blockchain data pipelines built on **Kafka + Avro**, designed to support:

* Multiple ingestion jobs:

  * `realtime` (tailing the chain head)
  * `backfill` (historical replay)
* Strong **deduplication**, **debuggability**, and **reproducibility**
* Safe **resume / recovery** after failures
* Compatibility with **multiple blockchains** (Ethereum, Solana, Sui, etc.)

The design assumes:

* Kafka as the transport layer
* Schema Registry + Avro for schema evolution
* Downstream systems such as Spark, ClickHouse, Iceberg, Delta Lake

---

## 2. Design Goals

### 2.1 Core Goals

1. **Exactly-once–friendly** semantics at the ingestion layer
2. Clear separation between:

   * *data events* (blocks, transactions)
   * *ingestion state* (progress tracking)
3. Support for **multiple concurrent jobs** without state corruption
4. Ability to **resume safely** after partial backfills
5. Enable downstream **deduplication** and **debugging**

### 2.2 Non-Goals

* This spec does **not** define transaction- or log-level schemas (can be layered later)
* Chain-specific fields are carried as opaque payloads

---

## 3. Kafka Topics Overview

| Topic Name                   | Type  | Cleanup Policy | Purpose                                |
| ---------------------------- | ----- | -------------- | -------------------------------------- |
| `blockchain.blocks`          | Data  | `delete`       | Canonical block data                   |
| `blockchain.ingestion_state` | State | `compact`      | Per-chain + per-job ingestion progress |

---

## 4. Common Concepts

### 4.1 Chain Identifier

A **logical identifier**, not tied to network IDs:

Examples:

* `eth-mainnet`
* `eth-goerli`
* `sol-mainnet`
* `sui-mainnet`

```text
chain_id = <blockchain>-<network>
```

---

### 4.2 Job Type

```text
job_type ∈ { "realtime", "backfill" }
```

* `realtime`: monotonic forward progress
* `backfill`: bounded historical replay

---

### 4.3 Run ID

A **globally unique identifier** per execution:

* UUID recommended
* Allows multiple runs of the same job_type

```text
run_id = uuid4()
```

---

## 5. Topic: `blockchain.blocks`

### 5.1 Purpose

Stores **immutable block events** emitted by any ingestion job.

* Multiple jobs may emit the *same block*
* Deduplication is handled downstream

---

### 5.2 Kafka Message Key (Avro)

```avro
{
  "type": "record",
  "name": "BlockKey",
  "namespace": "blockchain.blocks",
  "fields": [
    {"name": "chain_id", "type": "string"},
    {"name": "block_height", "type": "long"}
  ]
}
```

**Properties**:

* Stable across jobs
* Enables partition locality by block height

---

### 5.3 Kafka Message Value (Avro)

```avro
{
  "type": "record",
  "name": "BlockEvent",
  "namespace": "blockchain.blocks",
  "fields": [
    {"name": "chain_id", "type": "string"},
    {"name": "block_height", "type": "long"},
    {"name": "block_hash", "type": "string"},

    {"name": "job_type", "type": "string"},
    {"name": "run_id", "type": "string"},

    {"name": "insert_ts", "type": {"type": "long", "logicalType": "timestamp-millis"}},

    {
      "name": "block_payload",
      "type": "bytes",
      "doc": "Chain-specific block data (e.g. Ethereum JSON-RPC block response)"
    }
  ]
}
```

---

### 5.4 Deduplication Strategy

Downstream systems should deduplicate on:

```text
(chain_id, block_height, block_hash)
```

Optionally:

```text
(chain_id, block_height)
```

(depending on reorg handling strategy)

---

## 6. Topic: `blockchain.ingestion_state`

### 6.1 Purpose

Stores **authoritative ingestion progress** using Kafka log compaction.

* Exactly one *logical state* per (chain_id, job_type)
* Updated atomically with block writes (Kafka transactions)

---

### 6.2 Kafka Message Key (Avro)

```avro
{
  "type": "record",
  "name": "IngestionStateKey",
  "namespace": "blockchain.ingestion_state",
  "fields": [
    {"name": "chain_id", "type": "string"},
    {"name": "job_type", "type": "string"}
  ]
}
```

---

### 6.3 Kafka Message Value (Avro)

```avro
{
  "type": "record",
  "name": "IngestionState",
  "namespace": "blockchain.ingestion_state",
  "fields": [
    {"name": "chain_id", "type": "string"},
    {"name": "job_type", "type": "string"},

    {"name": "last_processed_block", "type": "long"},

    {"name": "run_id", "type": "string"},

    {"name": "updated_ts", "type": {"type": "long", "logicalType": "timestamp-millis"}},

    {
      "name": "status",
      "type": {
        "type": "enum",
        "name": "IngestionStatus",
        "symbols": ["RUNNING", "STOPPED", "COMPLETED", "FAILED"]
      }
    },

    {
      "name": "extra",
      "type": ["null", "string"],
      "default": null,
      "doc": "Optional debug metadata"
    }
  ]
}
```

---

### 6.4 State Semantics

| Job Type | Meaning of `last_processed_block`  |
| -------- | ---------------------------------- |
| realtime | Highest fully committed block      |
| backfill | Highest completed historical block |

Backfill jobs **must read this state before starting** to determine resume point.

---

## 7. Transactional Guarantees

Recommended producer behavior:

* Enable Kafka transactions
* For each batch:

  1. Produce N `blockchain.blocks` records
  2. Produce exactly one `blockchain.ingestion_state` update
  3. Commit transaction

This guarantees:

* No state advance without data
* No duplicate state on retry

---

## 8. Multi-Blockchain Compatibility

### 8.1 Why This Schema Is Generic

| Aspect       | Ethereum     | Solana        | Sui          |
| ------------ | ------------ | ------------- | ------------ |
| Block height | slot / block | slot          | checkpoint   |
| Payload      | JSON         | binary / JSON | binary / BCS |

All chain-specific differences are encapsulated in:

```text
block_payload: bytes
```

---

### 8.2 Future Extensions

Optional additional topics:

* `blockchain.transactions`
* `blockchain.logs`
* `blockchain.checkpoints` (Sui)

Using the same key pattern:

```text
(chain_id, height)
```

---

## 9. Operational Debugging Examples

### 9.1 Identify Duplicate Blocks

```sql
SELECT chain_id, block_height, COUNT(*)
FROM blocks
GROUP BY chain_id, block_height
HAVING COUNT(*) > 1;
```

---

### 9.2 Trace a Single Backfill Run

```sql
SELECT *
FROM blocks
WHERE run_id = '<run_id>'
ORDER BY block_height;
```

---

## 10. Summary

This ingestion schema provides:

* Clean separation of **data vs state**
* Strong support for **replay, resume, and deduplication**
* Safe coexistence of **realtime and backfill jobs**
* A future-proof foundation for **multi-chain ingestion**

It is suitable for production-grade blockchain data platforms.


