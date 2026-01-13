from hexbytes import HexBytes
from web3.datastructures import AttributeDict

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

def fetch_block_logs(web3_router, block_number):
    return web3_router.call(
        lambda w3: w3.eth.get_logs({"fromBlock": block_number, "toBlock": block_number})
    )
