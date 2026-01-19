import time
from typing import Optional, Tuple
from src.logging import log
from src.metrics import (
    CHAIN_LATEST_BLOCK,
    CHAIN_LATEST_BLOCK_RAW,
)

class SafeLatestBlockProvider:
    """
    Provide a validated, monotonic latest block number
    based on potentially unreliable RPC responses.
    """

    def __init__(
        self,
        chain: str,
        job: str,
        *,
        max_reorg_tolerance: int = 5,
        max_block_jump: int = 200,
    ):
        self.chain = chain
        self.job = job
        self.max_reorg_tolerance = max_reorg_tolerance
        self.max_block_jump = max_block_jump

        self._last_good_block: Optional[int] = None
        self._last_rpc: Optional[str] = None

    def update(
        self,
        raw_block: int,
        rpc_name: str,
    ) -> int:
        """
        Validate raw latest block and return a safe block number.
        """

        if self._last_good_block is None:
            safe_block = raw_block

        else:
            # 1️⃣ Severe regression → reject
            if raw_block < self._last_good_block - self.max_reorg_tolerance:
                log.warning(
                    "rpc_latest_block_regression",
                    extra={
                        "event": "rpc_latest_block_regression",
                        "chain": self.chain,
                        "job": self.job,
                        "rpc": rpc_name,
                        "raw_block": raw_block,
                        "last_good_block": self._last_good_block,
                    },
                )
                safe_block = self._last_good_block

            # 2️⃣ Abnormal forward jump → cap
            elif raw_block - self._last_good_block > self.max_block_jump:
                log.warning(
                    "rpc_latest_block_jump",
                    extra={
                        "event": "rpc_latest_block_jump",
                        "chain": self.chain,
                        "job": self.job,
                        "rpc": rpc_name,
                        "raw_block": raw_block,
                        "last_good_block": self._last_good_block,
                        "max_block_jump": self.max_block_jump,
                    },
                )
                safe_block = self._last_good_block + self.max_block_jump

            else:
                safe_block = raw_block

        # persist
        self._last_good_block = safe_block
        self._last_rpc = rpc_name

        # metrics
        CHAIN_LATEST_BLOCK_RAW.labels(
            chain=self.chain,
            job=self.job,
            rpc=rpc_name,
        ).set(raw_block)

        CHAIN_LATEST_BLOCK.labels(
            chain=self.chain,
            job=self.job,
        ).set(safe_block)

        return safe_block

    @property
    def last_good_block(self) -> Optional[int]:
        return self._last_good_block
