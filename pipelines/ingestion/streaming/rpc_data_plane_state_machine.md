```mermaid
stateDiagram-v2
    direction TD

    %% ========================
    %% Range lifecycle
    %% ========================
    [*] --> 
    
    RangePlanned : RangePlanner <br/> Generate RangeRecord (register / state machine)

    RangePlanned --> RangeRegistered : Registry.register(range)
    
    RangeRegistered --> TaskSubmitted : submit_range()<br/>Create RPC task
    TaskSubmitted --> InFlight : AsyncRpcScheduler.submit()

    %% ========================
    %% RPC execution
    %% ========================
    InFlight --> RpcSucceeded : RPC OK<br/>(RangeResult - logs, rpc, key)
    InFlight --> RpcFailed : RPC Exception<br/>RpcErrorResult

    %% ========================
    %% Success path
    %% ========================
    RpcSucceeded --> ResultBuffered : push OrderedBuffer<br/>(by range_id)
    ResultBuffered --> KafkaCommitted : EOS txn write
    KafkaCommitted --> RangeDone : Registry.drop(range)

    %% ========================
    %% Retry path
    %% ========================
    RpcFailed --> Retryable : error retryable<br/>retry < max_retry
    Retryable --> TaskSubmitted : backoff + resubmit<br/>(same range_id)

    RpcFailed --> FatalError : retry exhausted<br/>or non-retryable

    FatalError --> RangeFailed : mark failed<br/>emit metric / log
    RangeFailed --> RangeDone : Registry.drop(range)

    %% ========================
    %% Terminal
    %% ========================
    RangeDone --> [*]

```

```mermaid
stateDiagram-v2
    [*] --> PLANNED

    PLANNED: RangePlanner
    PLANNED --> DISPATCHED: submit range task

    DISPATCHED --> INFLIGHT: scheduler accepted
    INFLIGHT --> FETCHING: rpc_call_start

    FETCHING --> SUCCESS: logs fetched
    FETCHING --> RPC_ERROR: retryable error
    FETCHING --> FATAL_ERROR: non-retryable

    RPC_ERROR --> RETRY_WAIT: backoff
    RETRY_WAIT --> FETCHING

    RPC_ERROR --> FAILED: max retry exceeded
    FATAL_ERROR --> FAILED

    SUCCESS --> COMMITTING: kafka txn begin
    COMMITTING --> COMMITTED: txn commit
    COMMITTING --> COMMIT_FAILED

    COMMIT_FAILED --> COMMIT_RETRY
    COMMIT_RETRY --> COMMITTING

    COMMITTED --> ADVANCE_CURSOR
    ADVANCE_CURSOR --> [*]

    FAILED --> PARKED

    note right of PLANNED
      RangeRecord:
      - range_id
      - start_block
      - end_block
      - status
      - retry_count
    end note

    note right of COMMITTED
      cursor.advance()
      state persisted
    end note

    note right of PARKED
      Requires operator
      or delayed replay
    end note
```