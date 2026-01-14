import time, random
from collections import deque
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from src.rpc_context import set_current_rpc
from src.metrics import RPC_REQUESTS, RPC_ERRORS

# -----------------------------
# RPC Provider config
# -----------------------------
class RpcProvider:
    def __init__(self, name, url, weight):
        self.name = name
        self.url = url
        self.base_weight = weight
        self.current_weight = weight
        self.cooldown_until = 0
        self.errors = 0

    def available(self):
        return time.time() >= self.cooldown_until

    def penalize(self, seconds=10):
        self.errors += 1
        self.current_weight = max(1, self.current_weight - 1)
        self.cooldown_until = time.time() + seconds

    def reward(self):
        if self.current_weight < self.base_weight:
            self.current_weight += 1

class RpcPool:
    def __init__(self, providers):
        self.providers = providers
        self.queue = deque()

    def _rebuild_queue(self):
        self.queue.clear()
        for p in self.providers:
            if p.available():
                self.queue.extend([p] * p.current_weight)
        random.shuffle(self.queue)

    def pick(self):
        if not self.queue:
            self._rebuild_queue()
        if not self.queue:
            raise RuntimeError("No RPC provider available (all in cooldown)")
        return self.queue.popleft()




class Web3Router:
    def __init__(
        self,
        rpc_pool,
        max_attempts=None,
        penalize_seconds=15,
    ):
        self.rpc_pool = rpc_pool
        self.max_attempts = max_attempts or len(rpc_pool.providers)
        self.penalize_seconds = penalize_seconds

    def call(self, fn):
        last_exc = None
        attempted = set()

        for _ in range(self.max_attempts):
            provider = self.rpc_pool.pick()

            # 防止同一个 call 重复用同一个 provider
            if provider.name in attempted:
                continue
            attempted.add(provider.name)

            set_current_rpc(provider.name)
            RPC_REQUESTS.labels(rpc=provider.name).inc()

            w3 = Web3(
                Web3.HTTPProvider(
                    provider.url,
                    request_kwargs={
                        "timeout": 10,   # ⛔ 防止卡死
                    },
                )
            )
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            try:
                result = fn(w3)
                provider.reward()
                return result

            except Exception as e:
                last_exc = e

                provider.penalize(seconds=self.penalize_seconds)
                RPC_ERRORS.labels(rpc=provider.name).inc()

                # 🔥 关键：直接 failover，下一个
                continue

        # 所有 RPC 都失败
        raise RuntimeError(
            f"All RPC providers failed after {len(attempted)} attempts"
        ) from last_exc