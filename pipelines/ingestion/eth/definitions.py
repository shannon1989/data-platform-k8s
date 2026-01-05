from dagster import Definitions

from assets_backfill import eth_block_backfill

defs = Definitions(
    assets=[eth_block_backfill],
)
