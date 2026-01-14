from hexbytes import HexBytes
from web3.datastructures import AttributeDict
from datetime import datetime, timezone

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
def fetch_block_logs(web3_router, block_number):
    return web3_router.call(
        lambda w3: w3.eth.get_logs({"fromBlock": block_number, "toBlock": block_number})
    )

# -----------------------------
# create current_utctime
# -----------------------------
def current_utctime():
    """Return the current UTC time string in ISO-8601 format with millisecond precision"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
