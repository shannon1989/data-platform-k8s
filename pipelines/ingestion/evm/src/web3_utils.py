import time
from hexbytes import HexBytes
from web3.datastructures import AttributeDict
from datetime import datetime, timezone
from src.logging import log

# -----------------------------
# JSON safe serialization
# -----------------------------
def to_json_safe(obj):
    if isinstance(obj, HexBytes):
        return obj.hex()
    elif isinstance(obj, AttributeDict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_json_safe(v) for v in obj]
    else:
        return obj

# -----------------------------
# Web3 initialization with router
# -----------------------------
def fetch_range_logs(
    web3_router,
    start_block,
    end_block,
    with_provider: bool = True,
    *,
    max_retry: int = 10,
    retry_sleep: float = 0.5,
):
    """
    Fetch logs for a range of blocks with retry on empty result.

    Retry condition:
        - RPC returns [] (empty logs)

    Returns:
        - with_provider=False:
            logs
        - with_provider=True:
            (logs, rpc_name)

    Raises:
        RuntimeError if empty logs after max_retry
    """

    last_provider = None
    
    for attempt in range(1, max_retry + 1):
        if with_provider:
            logs, provider_ctx = web3_router.call_with_provider(
                lambda w3: w3.eth.get_logs(
                    {"fromBlock": start_block, "toBlock": end_block}
                )
            )
            last_provider = provider_ctx
        else:
            logs = web3_router.call(
                lambda w3: w3.eth.get_logs(
                    {"fromBlock": start_block, "toBlock": end_block}
                )
            )

        # ✅ 正常返回（非空）
        if logs:
            return (logs, last_provider) if with_provider else logs

        # ⚠️ 空 logs → retry
        log.warning(
            "⚠️empty_range_logs_retry",
            extra={
                # "event": "empty_range_logs_retry",
                "range_start": start_block,
                "range_end": end_block,
                "attempt": attempt,
                "max_retry": max_retry,
                "rpc": last_provider.rpc,
                "key_env": last_provider.key_env,
            },
        )

        # 👉 切 RPC（非常关键）
        web3_router.rotate_provider() # cooldown 5s seconds=5

        time.sleep(retry_sleep)

    # ❌ retry exhausted
    raise RuntimeError(
        f"empty logs after {max_retry} retries: "
        f"{start_block}-{end_block}"
    )


# -----------------------------
# create current_utctime
# -----------------------------
def current_utctime():
    """Return the current UTC time string in ISO-8601 format with millisecond precision"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
