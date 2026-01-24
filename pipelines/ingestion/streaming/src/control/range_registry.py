from .range_record import RangeRecord
from .range_status import RangeStatus

# -------------------------
# single source of truth”
# 生命周期管理器
# 不关心 RPC / Kafka
# -------------------------
class RangeRegistry:
    """
    Single source of truth for range lifecycle.
    """

    def __init__(self):
        self._ranges: dict[int, RangeRecord] = {}

    # -------------------------
    # register
    # -------------------------
    def register(self, range_id: int, start_block: int, end_block: int) -> RangeRecord:
        if range_id in self._ranges:
            raise RuntimeError(f"range {range_id} already registered")

        r = RangeRecord(
            range_id=range_id,
            start_block=start_block,
            end_block=end_block,
        )
        self._ranges[range_id] = r
        return r

    # -------------------------
    # lookup
    # -------------------------
    def get(self, range_id: int) -> RangeRecord:
        try:
            return self._ranges[range_id]
        except KeyError:
            raise KeyError(f"range {range_id} not found")

    # -------------------------
    # state transitions
    # -------------------------
    def mark_inflight(self, range_id: int, task_id: int):
        r = self.get(range_id)
        r.status = RangeStatus.INFLIGHT
        r.last_task_id = task_id
        r.touch()

    def mark_done(self, range_id: int):
        r = self.get(range_id)
        r.status = RangeStatus.DONE
        r.touch()
        self._ranges.pop(range_id, None)

    def mark_failed(self, range_id: int, error: str):
        r = self.get(range_id)
        r.status = RangeStatus.FAILED
        r.last_error = error
        r.touch()
        self._ranges.pop(range_id, None)

    # -------------------------
    # retry logic
    # -------------------------
    def mark_retry(self, range_id: int, error: str) -> bool:
        """
        Returns True if retry allowed, False if exhausted.
        """
        r = self.get(range_id)

        r.retry += 1
        r.last_error = error
        r.touch()

        if r.retry > r.max_retry:
            r.status = RangeStatus.FAILED
            return False

        r.status = RangeStatus.RETRYING
        return True

    # -------------------------
    # helpers
    # -------------------------
    def inflight_count(self) -> int:
        return sum(1 for r in self._ranges.values() if r.status == RangeStatus.INFLIGHT)

    def active_ranges(self) -> list[RangeRecord]:
        return [
            r for r in self._ranges.values()
            if r.status not in (RangeStatus.DONE, RangeStatus.FAILED)
        ]