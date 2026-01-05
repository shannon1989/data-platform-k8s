# -----------------------------
# Date → unix timestamp (UTC) [start, end)
# -----------------------------
def date_to_timestamp(date_str: str, end: bool = False) -> int:
    """
    date_str: 'YYYY-MM-DD'
    end=False  -> Current Date 00:00:00 UTC
    end=True   -> Next Day 00:00:00 UTC
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    dt = dt.replace(tzinfo=timezone.utc)

    if end:
        dt = dt + timedelta(days=1)

    return int(dt.timestamp())
  


# -----------------------------
# utility func：date range → block range
# -----------------------------
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
