import os
import time
import random
import asyncio
from typing import NamedTuple, Optional
from aiohttp import ClientSession, ClientTimeout
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from src.metrics import RPC_REQUESTS, RPC_ERRORS, RPC_KEY_BUSY, ACTIVE_RPC_CONNECTIONS
from src.logging import log

# -----------------------------
# Exceptions
# -----------------------------
class RpcKeyUnavailable(Exception): pass
class RpcTemporarilyUnavailable(Exception): pass

# -----------------------------
# RPC Key Slot: 滑动窗口频率控制
# -----------------------------
class RpcKeySlot:
    def __init__(self, key_env: str, min_interval: float):
        self.key_env = key_env
        self.min_interval = min_interval
        self.last_used_at = 0.0
        self.lock = asyncio.Lock()

    async def try_acquire(self) -> bool:
        async with self.lock:
            now = time.time()
            if now - self.last_used_at < self.min_interval:
                return False
            self.last_used_at = now
            return True

# -----------------------------
# RPC Provider
# -----------------------------
class RpcProvider:
    def __init__(self, name, base_url, weight, key_env=None, key_interval=1.0):
        self.name = name
        self.base_weight = weight
        self.current_weight = weight
        self.cooldown_until = 0

        self.key_slots = []
        if key_env:
            if not isinstance(key_env, list):
                key_env = [key_env]
            self.key_slots = [RpcKeySlot(env, key_interval) for env in key_env]

        self._key_cursor = 0

    def available(self) -> bool:
        return time.time() >= self.cooldown_until

    def penalize(self, seconds=15):
        self.current_weight = max(1, self.current_weight - 1)
        self.cooldown_until = time.time() + seconds

    def reward(self):
        if self.current_weight < self.base_weight:
            self.current_weight += 1

    async def acquire_key(self, max_wait=2.0, sleep_step=0.05):
        """异步滑动窗口获取 key"""
        if not self.key_slots:
            return self.base_url, None  # 公共 RPC

        deadline = time.time() + max_wait
        while time.time() < deadline:
            for _ in range(len(self.key_slots)):
                slot = self.key_slots[self._key_cursor]
                self._key_cursor = (self._key_cursor + 1) % len(self.key_slots)
                if await slot.try_acquire():
                    api_key = os.getenv(slot.key_env)
                    if api_key:
                        return f"{self.base_url}/{api_key}", slot
            await asyncio.sleep(sleep_step)
        raise RpcKeyUnavailable(f"No available RPC key for provider={self.name}")


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

    @classmethod
    def from_config(cls, rpc_configs: dict, chain: str) -> "RpcPool":
        chain_cfg = rpc_configs.get("chains", {}).get(chain)
        if not chain_cfg:
            raise RuntimeError(f"Chain config not found: {chain}")

        providers = []
        for cfg in chain_cfg.get("providers", []):
            if not cfg.get("enabled", True):
                continue
            providers.append(RpcProvider(
                name=cfg["name"],
                base_url=cfg["base_url"],
                weight=int(cfg.get("weight", 1)),
                key_env=cfg.get("api_key_env"),
            ))

        if not providers:
            raise RuntimeError(f"No RPC providers enabled for chain: {chain}")

        for p in providers:
            log.info(
                "rpc_enabled",
                extra={
                    "chain": chain,
                    "rpc": p.name,
                    "key_envs": [k.key_env for k in p.key_slots] if p.key_slots else ["public"],
                    "weight": p.base_weight,
                },
            )

        return cls(providers)


class RpcContext(NamedTuple):
    rpc: str
    key_env: str

# -----------------------------
# 异步滑动窗口 RPC router
# -----------------------------
class Web3AsyncSlidingRouter:
    def __init__(self, rpc_pool: RpcPool, chain: str, timeout=10, penalize_seconds=15, max_backoff=30):
        self.rpc_pool = rpc_pool
        self.chain = chain
        self.timeout = timeout
        self.penalize_seconds = penalize_seconds
        self.max_backoff = max_backoff
        self.consecutive_failures = 0

    async def call(self, fn):
        """异步滑动窗口 RPC 调用"""
        last_exc = None
        providers = self.rpc_pool.get_available_providers()
        used = set()

        for provider in providers:
            if provider.name in used:
                continue
            used.add(provider.name)

            try:
                url, slot = await provider.acquire_key()
            except RpcKeyUnavailable:
                RPC_KEY_BUSY.labels(chain=self.chain, rpc=provider.name).inc()
                continue

            key_env_label = slot.key_env if slot else "public"
            RPC_REQUESTS.labels(chain=self.chain, rpc=provider.name, key_env=key_env_label).inc()
            ACTIVE_RPC_CONNECTIONS.labels(chain=self.chain, rpc=provider.name).inc()

            timeout = ClientTimeout(total=self.timeout)
            async with ClientSession(timeout=timeout) as session:
                w3 = Web3(Web3.AsyncHTTPProvider(url, session=session))
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

                try:
                    # 异步调用用户传入的 fn
                    result = await fn(w3)
                    provider.reward()
                    self.consecutive_failures = 0
                    return result, RpcContext(rpc=provider.name, key_env=key_env_label)

                except Exception as e:
                    log.warning(
                        "⚠️ rpc_failover",
                        extra={
                            "chain": self.chain,
                            "rpc": provider.name,
                            "key_env": key_env_label,
                            "error": str(e)[:200],
                        },
                    )
                    RPC_ERRORS.labels(chain=self.chain, rpc=provider.name, key_env=key_env_label).inc()
                    provider.penalize(self.penalize_seconds)
                    last_exc = e
                finally:
                    ACTIVE_RPC_CONNECTIONS.labels(chain=self.chain, rpc=provider.name).dec()

        # 全部失败 → 指数回退
        self.consecutive_failures += 1
        backoff = min(5 * self.consecutive_failures, self.max_backoff)
        await asyncio.sleep(backoff)
        raise RpcTemporarilyUnavailable(f"RPC temporarily unavailable for chain={self.chain}") from last_exc
