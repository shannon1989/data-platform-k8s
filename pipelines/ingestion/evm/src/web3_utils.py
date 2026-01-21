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
    verify_multiple_providers: bool = True,  # 是否多 provider 验证
):
    """
    Fetch logs for a range of blocks with retry on empty result.

    Strategy:
    1. If logs are non-empty → return immediately
    2. If logs are empty:
        - Check block.transactions
            - 0 → real empty block → return []
            - >0 → possibly RPC limitation → retry / rotate provider
        - Optionally, verify across multiple providers to reduce unreliable RPC issues
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

        # ⚡ logs 为空 → 先判断区块交易数
        block_tx_count = web3_router.call(lambda w3: len(w3.eth.get_block(start_block).transactions))
        if block_tx_count == 0:
            # 真空块，不再 retry
            log.info(
                "⚠️empty_block_no_logs",
                extra={
                    "range_start": start_block,
                    "range_end": end_block,
                    "rpc": last_provider.rpc if last_provider else None,
                },
            )
            return ([], last_provider) if with_provider else []
        
        # 🔍 多 provider 验证空 logs (当 logs 为空但交易数 >0 时，调用 2 个不同 provider 再拉一次 logs)
        if verify_multiple_providers:
            reliable_logs_found = False
            for _ in range(2):  # 检查 2 个不同 provider
                logs2, provider2 = web3_router.call_with_provider(
                    lambda w3: w3.eth.get_logs({"fromBlock": start_block, "toBlock": end_block})
                )
                if logs2:
                    reliable_logs_found = True
                    logs = logs2
                    last_provider = provider2
                    break
            if reliable_logs_found:
                return (logs, last_provider) if with_provider else logs
        
        
        # logs 为空但 block 有交易 → 可能 RPC 限制 → retry
        log.warning(
            "⚠️empty_range_logs_retry",
            extra={
                # "event": "empty_range_logs_retry",
                "range_start": start_block,
                "range_end": end_block,
                "attempt": attempt,
                "max_retry": max_retry,
                "rpc": last_provider.rpc if last_provider else None,
                "key_env": last_provider.key_env if last_provider else None,
            },
        )
                
        # 👉 切 RPC
        web3_router.rotate_provider() # cooldown 5s seconds=5

        time.sleep(retry_sleep)

    # ❌ retry exhausted (10 RPC Down)
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
