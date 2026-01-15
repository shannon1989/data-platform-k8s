import time, random
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


class RpcTemporarilyUnavailable(Exception):
    pass

class Web3Router:
    def __init__(
        self,
        rpc_pool,
        chain: str,
        timeout=10,
        penalize_seconds=15,
        max_backoff=30,
    ):
        self.rpc_pool = rpc_pool
        self.chain = chain
        self.timeout = timeout
        self.penalize_seconds = penalize_seconds
        self.max_backoff = max_backoff

        self.consecutive_failures = 0  # ⭐ 关键状态

    def call(self, fn):
        last_exc = None

        providers = self.rpc_pool.get_available_providers()
        used = set()

        for provider in providers:
            if provider.name in used:
                continue
            used.add(provider.name)

            set_current_rpc(provider.name)
            RPC_REQUESTS.labels(chain=self.chain, rpc=provider.name).inc()

            w3 = Web3(
                Web3.HTTPProvider(
                    provider.url,
                    request_kwargs={"timeout": self.timeout},
                )
            )
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            try:
                result = fn(w3)

                # ✅ 成功路径：恢复权重 & 清零失败计数
                provider.reward()
                self.consecutive_failures = 0
                return result

            except Exception as e:
                log.warning(
                    "rpc_failover",
                    extra={
                        "event": "rpc_failover",
                        "chain": self.chain,
                        "rpc": provider.name,
                        "error": str(e)[:200],
                    },
                )
                RPC_ERRORS.labels(chain=self.chain, rpc=provider.name).inc()
                provider.penalize(self.penalize_seconds)
                last_exc = e
                continue  # 🔥 立刻换下一个

        # ❌ 本轮所有 RPC 都失败
        self.consecutive_failures += 1

        backoff = min(5 * self.consecutive_failures, self.max_backoff)

        log.error(
            "rpc_round_failed",
            extra={
                "event": "rpc_round_failed",
                "chain": self.chain,
                "attempted": list(used),
                "consecutive_failures": self.consecutive_failures,
                "backoff_seconds": backoff,
            },
        )

        # 🌙 关键：睡一会，而不是 raise
        time.sleep(backoff)

        # ❗不抛异常，让上层继续 while True
        raise RpcTemporarilyUnavailable(
            f"RPC temporarily unavailable for chain={self.chain}"
        ) from last_exc