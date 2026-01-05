
BASE_URL = "https://api.etherscan.io/v2/api?chainid=1"



# -----------------------------
# Etherscan: timestamp → block number
# -----------------------------
def get_block_no_by_time(
    unix_timestamp: int,
    closest: str,
    max_retries: int = 3,
) -> int:
    """
    closest: 'before' | 'after'
    """
    assert closest in ("before", "after")

    params = {
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": unix_timestamp,
        "closest": closest,
        "apikey": ETHERSCAN_API_KEY,
    }

    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(BASE_URL, params=params, timeout=10)
            res.raise_for_status()

            data = res.json()
            result = data.get("result")

            if result is None:
                raise RuntimeError(f"Empty result: {data}")

            return int(result)

        except Exception as e:
            print(
                f"❌ getblocknobytime failed "
                f"(ts={unix_timestamp}, closest={closest}, attempt={attempt}): {e}",
                flush=True,
            )
            time.sleep(2)

    raise RuntimeError("Failed t