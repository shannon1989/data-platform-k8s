from typing import Optional
from .block_range import BlockRange

# -------------------------
# 顺序生成
# 不感知执行结果
# 不 retry
# -------------------------
class RangePlanner:
    """
    只负责：在 latest_block 允许的情况下，持续生成新的 block ranges
    """
    def __init__(self, start_block: int, range_size: int):
        self._next_block = start_block
        self._range_size = range_size
        self._next_range_id = 0

    def next_range(self, latest_block: int) -> Optional[BlockRange]:
        """
        返回下一个可提交的 BlockRange
        如果当前链高度还不够，返回 None
        """
        if self._next_block > latest_block:
            return None

        start = self._next_block
        end = min(
            start + self._range_size - 1,
            latest_block,
        )

        r = BlockRange(
            range_id=self._next_range_id,
            start_block=start,
            end_block=end,
        )

        # 👉 推进游标
        self._next_block = end + 1
        self._next_range_id += 1

        return r