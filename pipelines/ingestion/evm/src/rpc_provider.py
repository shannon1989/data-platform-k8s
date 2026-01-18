import time, random
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from src.rpc_context import set_current_rpc, get_current_rpc
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
        before = self.current_weight
        self.current_weight = max(1, self.current_weight - 1)
        self.cooldown_until = time.time() + seconds

        log.warning(
            "rpc_penalized",
            extra={
                "event": "rpc_penalized",
                "rpc": self.name,
                "weight_before": before,
                "weight_after": self.current_weight,
                "cooldown_seconds": seconds,
            },
        )

    def reward(self):
        if self.current_weight < self.base_weight:
            before = self.current_weight
            self.current_weight += 1

            log.info(
                "rpc_rewarded",
                extra={
                    "event": "rpc_rewarded",
                    "rpc": self.name,
                    "weight_before": before,
                    "weight_after": self.current_weight,
                },
            )



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
    
    # ⭐ 新增
    def get_provider(self, name: str):
        for p in self.providers:
            if p.name == name:
                return p
        return None

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

    # -------------------------------------------------
    # 🔒 Internal unified call
    # -------------------------------------------------
    def _call_internal(self, fn, return_provider: bool = False):
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

                # ✅ 成功路径
                provider.reward()
                self.consecutive_failures = 0

                # 功的路径不打印
                # log.info(
                #     "rpc_call_success",
                #     extra={
                #         "event": "rpc_call_success",
                #         "chain": self.chain,
                #         "rpc": provider.name,
                #         "current_weight": provider.current_weight,
                #         "base_weight": provider.base_weight,
                #         "cooldown": not provider.available(),
                #     },
                # )
                
                if return_provider:
                    return result, provider.name
                return result

            except Exception as e:
                log.warning(
                    "rpc_failover",
                    extra={
                        # "event": "rpc_failover",
                        "chain": self.chain,
                        "rpc": provider.name,
                        "error": str(e)[:200],
                    },
                )
                RPC_ERRORS.labels(chain=self.chain, rpc=provider.name).inc()
                provider.penalize(self.penalize_seconds)
                last_exc = e
                continue

        # ❌ 本轮全部失败
        self.consecutive_failures += 1
        backoff = min(5 * self.consecutive_failures, self.max_backoff)

        log.error(
            "rpc_round_failed",
            extra={
                # "event": "rpc_round_failed",
                "chain": self.chain,
                "attempted": list(used),
                "consecutive_failures": self.consecutive_failures,
                "backoff_seconds": backoff,
            },
        )

        time.sleep(backoff)

        raise RpcTemporarilyUnavailable(
            f"RPC temporarily unavailable for chain={self.chain}"
        ) from last_exc

    # -------------------------------------------------
    # 🧱 Public APIs
    # -------------------------------------------------
    def call(self, fn):
        """Backward-compatible API"""
        return self._call_internal(fn, return_provider=False)

    def call_with_provider(self, fn):
        """
        New API:
        Returns (result, rpc_name)
        """
        return self._call_internal(fn, return_provider=True)


    def rotate_provider(self, seconds: int | None = None):
        """
        Force current RPC into cooldown to rotate provider.

        This is a soft rotate:
        - penalize current provider
        - next call will naturally pick another one

        Args:
            seconds: override penalize_seconds if provided
        """
        rpc_name = get_current_rpc()
        if not rpc_name:
            return

        provider = self.rpc_pool.get_provider(rpc_name)
        if not provider:
            return

        cooldown = seconds or self.penalize_seconds

        provider.penalize(cooldown)

        log.info(
            "rpc_rotated",
            extra={
                "event": "rpc_rotated",
                "chain": self.chain,
                "rpc": rpc_name,
                "cooldown_seconds": cooldown,
            },
        )