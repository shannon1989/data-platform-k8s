import asyncio
import aiohttp
import json
import time
import asyncio
from src.logging import log
from src.rpc_provider import RpcPool

# 外部链状态
# 弱一致
# 不应和 ingestion 强绑定
class UnifiedLatestBlockTracker:
    def __init__(
        self,
        *,
        router,
        rpc_pool,
        http_interval: float = 15.0,
        ws_stale_after: float = 15.0,
        max_reorg_tolerance: int = 5,
        max_forward_gap: int = 100,
    ):
        self.router = router
        self.rpc_pool = rpc_pool

        self.http_interval = http_interval
        self.ws_stale_after = ws_stale_after

        self.max_reorg_tolerance = max_reorg_tolerance
        self.max_forward_gap = max_forward_gap

        self._latest: int | None = None
        self._last_raw: int | None = None

        self._last_ws_block: int | None = None
        self._last_ws_ts: float = 0

        self._last_http_block: int | None = None
        self._last_http_ts: float = 0

        self._lock = asyncio.Lock()
        self._tasks: list[asyncio.Task] = []
        self._stopped = False

    # ======================
    # Public API
    # ======================

    def get_cached(self) -> int | None:
        return self._latest

    def start(self):
        self._tasks.append(asyncio.create_task(self._http_loop()))
        self._tasks.append(asyncio.create_task(self._ws_loop()))
        self._tasks.append(asyncio.create_task(self._arbiter_loop()))

    async def stop(self):
        self._stopped = True
        for t in self._tasks:
            t.cancel()

    # ======================
    # HTTP source
    # ======================

    async def _http_loop(self):
        while not self._stopped:
            try:
                bn = await self.router.get_latest_block()
                self._last_http_block = bn
                self._last_http_ts = time.time()
            except Exception as e:
                log.warning("⚠️ http_latest_failed", extra={"error": str(e)})

            await asyncio.sleep(self.http_interval)

    # ======================
    # WS source
    # ======================

    async def _ws_loop(self):
        while not self._stopped:
            ws_provider = None
            try:
                ws_pool = RpcPool(
                    providers=[p for p in self.rpc_pool.all_providers() if p.ws_url]
                )
                ws_provider = ws_pool.pick_ws_provider()
                if not ws_provider:
                    raise RuntimeError("no_ws_provider")

                ws_url, key_env = await ws_provider.acquire_ws_url()
                log.info("🔌 ws_connect", extra={"rpc": ws_provider.name, "key": key_env})

                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(ws_url, heartbeat=30) as ws:
                        await ws.send_json({
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "eth_subscribe",
                            "params": ["newHeads"],
                        })

                        async for msg in ws:
                            data = json.loads(msg.data)
                            if data.get("method") != "eth_subscription":
                                continue

                            bn_hex = data["params"]["result"].get("number")
                            if bn_hex:
                                self._last_ws_block = int(bn_hex, 16)
                                self._last_ws_ts = time.time()

            except Exception as e:
                log.warning(
                    "⚠️ ws_failed",
                    extra={"rpc": getattr(ws_provider, "name", None), "error": str(e)},
                )
                await asyncio.sleep(1)

    # ======================
    # Arbiter (核心)
    # ======================

    async def _arbiter_loop(self):
        while not self._stopped:
            async with self._lock:
                now = time.time()

                ws_healthy = (
                    self._last_ws_block is not None
                    and now - self._last_ws_ts <= self.ws_stale_after
                )

                if ws_healthy:
                    candidate = self._last_ws_block
                    source = "ws"
                else:
                    candidate = self._last_http_block
                    source = "http"

                if candidate is not None:
                    self._apply_candidate(candidate, source)

            await asyncio.sleep(0.5)

    # ======================
    # Candidate logic
    # ======================

    def _apply_candidate(self, candidate: int, source: str):
        self._last_raw = candidate

        if self._latest is None:
            self._latest = candidate
            log.info("📌 latest_initialized", extra={"latest": candidate, "src": source})
            return

        current = self._latest

        if candidate == current:
            return

        if candidate < current:
            delta = current - candidate
            if delta <= self.max_reorg_tolerance:
                self._latest = candidate
                log.warning(
                    "🔄 reorg",
                    extra={"from": current, "to": candidate, "src": source},
                )
            return

        gap = candidate - current
        if gap > self.max_forward_gap:
            capped = current + self.max_forward_gap
            self._latest = capped
            log.warning(
                "⚠️ forward_jump",
                extra={"candidate": candidate, "capped": capped, "src": source},
            )
            return

        self._latest = candidate
