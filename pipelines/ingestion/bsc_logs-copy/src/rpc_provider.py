import time, random
from collections import deque
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from src.rpc_context import set_current_rpc
from src.metrics import RPC_REQUESTS, RPC_ERRORS
from src.logging import log

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

    def available(self):
        return time.time() >= self.cooldown_until

    def penalize(self, seconds=15):
        self.current_weight = max(1, self.current_weight - 1)
        self.cooldown_until = time.time() + seconds

    def reward(self):
        if self.current_weight < self.base_weight:
            self.current_weight += 1


class RpcPool:
    def __init__(self, providers):
        self.providers = providers

    def get_available_providers(self):
        candidates = []
        for p in self.providers:
            if p.available():
                candidates.extend([p] * p.current_weight)

        random.shuffle(candidates)
        return candidates


class Web3Router:
    def __init__(self, rpc_pool, timeout=10, penalize_seconds=15):
        self.rpc_pool = rpc_pool
        self.timeout = timeout
        self.penalize_seconds = penalize_seconds

    def call(self, fn):
        last_exc = None

        providers = self.rpc_pool.get_available_providers()
        used = set()

        for provider in providers:
            if provider.name in used:
                continue
            used.add(provider.name)

            set_current_rpc(provider.name)
            RPC_REQUESTS.labels(rpc=provider.name).inc()

            w3 = Web3(
                Web3.HTTPProvider(
                    provider.url,
                    request_kwargs={"timeout": self.timeout},
                )
            )
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            try:
                result = fn(w3)
                provider.reward()
                return result

            except Exception as e:
                log.warning(
                    "rpc_failover",
                    extra={
                        "event": "rpc_failover",
                        "rpc": provider.name,
                        "error": str(e)[:200],
                    },
                )
                RPC_ERRORS.labels(rpc=provider.name).inc()
                last_exc = e
                provider.penalize(self.penalize_seconds)
                continue  # 🔥 立刻换下一个

        # 注意：这里只说明「这一轮不可用」
        log.error(
            "rpc_round_failed",
            extra={
                "event": "rpc_round_failed",
                "attempted": list(used),
            },
        )

        raise print("All RPC providers failed in this round") from last_exc
