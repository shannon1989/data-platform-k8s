import asyncio
from src.logging import log

# 外部链状态
# 弱一致
# 不应和 ingestion 强绑定
class LatestBlockTracker:
    def __init__(self, router, refresh_interval=2.0):
        self.router = router
        self.refresh_interval = refresh_interval
        self._latest: int | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._stopped = False

    def get_cached(self) -> int | None:
        """
        永不 await RPC, 只读缓存
        """
        return self._latest

    async def _refresh_loop(self):
        while not self._stopped:
            try:
                latest = await self.router.get_latest_block()
                async with self._lock:
                    self._latest = latest
            except Exception as e:
                log.warning(
                    "⚠️ latest_block_refresh_failed",
                    extra={"error": str(e)},
                )
            await asyncio.sleep(self.refresh_interval)

    def start(self):
        if not self._task:
            self._task = asyncio.create_task(self._refresh_loop())

    async def stop(self):
        self._stopped = True
        if self._task:
            await self._task

