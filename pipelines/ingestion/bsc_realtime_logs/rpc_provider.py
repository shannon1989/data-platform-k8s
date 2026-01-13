import time, random
from collections import deque
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from src.rpc_context import set_current_rpc
from pipelines.ingestion.bsc_realtime_logs.metrics import RPC_REQUESTS, RPC_ERRORS

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
            raise RuntimeError("No RPC provider available")
        return self.queue.popleft()

class Web3Router:
    def __init__(self, rpc_pool: RpcPool):
        self.rpc_pool = rpc_pool

    def call(self, fn):
        provider = self.rpc_pool.pick()
        set_current_rpc(provider.name)
        w3 = Web3(Web3.HTTPProvider(provider.url))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        try:
            result = fn(w3)
            provider.reward()
            RPC_REQUESTS.labels(rpc=provider.name).inc()
            return result
        except Exception:
            provider.penalize()
            RPC_ERRORS.labels(rpc=provider.name).inc()
            raise
