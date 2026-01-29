from datetime import datetime, timezone

# -----------------------------
# create current_utctime
# -----------------------------
def current_utctime():
    """Return the current UTC time string in ISO-8601 format with millisecond precision"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def build_method_group_map(chain_cfg: dict) -> dict[str, str]:
    """
    eth_getLogs -> heavy
    eth_blockNumber -> light
    """
    mapping = {}
    for group, methods in chain_cfg.get("method_groups", {}).items():
        for m in methods:
            mapping[m] = group
    return mapping

