import os
import requests
import time
from typing import Tuple
from datetime import datetime, timedelta, timezone

ETHERSCAN_CHAIN_ID = 1
ETHERSCAN_API_URL = os.getenv("ETH_ETHERSCAN_API_URL", f"https://api.etherscan.io/v2/api?chainid={ETHERSCAN_CHAIN_ID}")

ETHERSCAN_API_KEY = os.getenv("ETH_ETHERSCAN_API_KEY", "<YOUR_API_KEY>")

if not ETHERSCAN_API_KEY or "<YOUR_API_KEY>" in ETHERSCAN_API_KEY:
    raise RuntimeError("ETH_ETHERSCAN_API_KEY is not configured")

# ----------------------------------------
# Date → unix timestamp (UTC) [start, end)
# ----------------------------------------
def date_to_timestamp(date_str: str, end: bool = False) -> int:
    """
    date_str: 'YYYY-MM-DD'
    end=False  -> Day + 0 Date 00:00:00 UTC
    end=True   -> Day + 1 Date 00:00:00 UTC
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    dt = dt.replace(tzinfo=timezone.utc)

    if end:
        dt = dt + timedelta(days=1)

    return int(dt.timestamp())


# ----------------------------------------
#Etherscan: timestamp → block number
# ----------------------------------------
def get_block_no_by_time(
    unix_timestamp: int,
    closest: str,
    max_retries: int = 3,
) -> int:
    """
    closest: 'before' | 'after'
    """
    assert closest in ("before", "after") , f"closest must be 'before' or 'after', got: {closest}"

    params = {
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": unix_timestamp,
        "closest": closest,
        "apikey": ETHERSCAN_API_KEY,
    }

    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(ETHERSCAN_API_URL, params=params, timeout=10)
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
                flush=True, # Avoid output buffering and print immediately
            )
            time.sleep(2)

    raise RuntimeError("Failed to resolve block number by time")


# ----------------------------------------
# Convert：date range → block range
# ----------------------------------------
def get_block_range_by_date(
    start_date: str,
    end_date: str,
) -> Tuple[int, int]:
    """
    Input:
      start_date: 'YYYY-MM-DD'
      end_date:   'YYYY-MM-DD'

    Apply:
      [start_date 00:00:00,
       end_date+1 00:00:00)
    """

    if start_date > end_date:
        raise ValueError("start_date > end_date")

    start_ts = date_to_timestamp(start_date, end=False)
    end_ts = date_to_timestamp(end_date, end=True)

    start_block = get_block_no_by_time(
        unix_timestamp=start_ts,
        closest="after",
    )

    end_block = get_block_no_by_time(
        unix_timestamp=end_ts,
        closest="before",
    )

    if start_block > end_block:
        raise RuntimeError(
            f"Invalid block range: {start_block} > {end_block}"
        )

    print(
        f"Date range {start_date} ~ {end_date} "
        f"→ blocks [{start_block}, {end_block}]",
        flush=True,
    )

    return start_block, end_block

# Demo
if __name__ == "__main__":
    start_date = '2026-01-02'
    end_date = '2026-01-03'
    start_block, end_block = get_block_range_by_date(start_date, end_date)