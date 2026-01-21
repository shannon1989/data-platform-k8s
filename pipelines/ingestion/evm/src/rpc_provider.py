import time, random, os, threading
from typing import NamedTuple
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from src.metrics import RPC_REQUESTS, RPC_ERRORS, RPC_KEY_BUSY, ACTIVE_RPC_CONNECTIONS
from src.logging import log


# -----------------------------
# RPC key management config (batch dimention)
# -----------------------------
class BatchKeyManager:
    """
    Ensures key uniqueness within ONE batch.
    """
    def __init__(self):
        self._used_keys: set[str] = set()
        self._lock = threading.Lock()

    def try_acquire(self, key_env: str) -> bool:
        with self._lock:
            if key_env in self._used_keys:
                return False
            self._used_keys.add(key_env)
            return True

    def reset(self):
        with self._lock:
            self._used_keys.clear()


# -----------------------------
# RPC key management config (time dimention)
# -----------------------------
class RpcKeySlot:
    def __init__(self, key_env: str, min_interval: float):
        self.key_env = key_env
        self.min_interval = min_interval
        self.last_used_at = 0.0
        self.in_use = False
        self.lock = threading.Lock()

    def try_acquire(self) -> bool:
        now = time.time()
        with self.lock:
            if self.in_use:
                return False
            if now - self.last_used_at < self.min_interval:
                return False

            self.in_use = True
            self.last_used_at = now
            return True

    def release(self):
        with self.lock:
            self.in_use = False



# to store rpc name and key_env
class RpcContext(NamedTuple):
    rpc: str
    key_env: str # 明确：单值，不允许 list


# -----------------------------
# RPC Provider config
# -----------------------------
class RpcProvider:
    def __init__(self, name, base_url, weight, key_env=None, key_interval=1.0):
        self.name = name
        self.base_url = base_url 
        self.key_env = key_env
        self.base_weight = weight
        self.current_weight = weight
        self.cooldown_until = 0
        self.key_slots = []
        
        if key_env:
            if not isinstance(key_env, list):
                key_env = [key_env]

            self.key_slots = [
                RpcKeySlot(env, key_interval)
                for env in key_env
            ]
            
        self._key_cursor = 0
        
    def available(self):
        return time.time() >= self.cooldown_until

    def penalize(self, seconds=15):
        before = self.current_weight
        self.current_weight = max(1, self.current_weight - 1)
        self.cooldown_until = time.time() + seconds

        # log.warning(
        #     "⚠️ rpc_penalized",
        #     extra={
        #         # "event": "rpc_penalized",
        #         "rpc": self.name,
        #         "weight_before": before,
        #         "weight_after": self.current_weight,
        #         "cooldown_seconds": seconds,
        #     },
        # )
        
    def reward(self):
        if self.current_weight < self.base_weight:
            before = self.current_weight
            self.current_weight += 1

            # log.info(
            #     "rpc_rewarded",
            #     extra={
            #         "event": "rpc_rewarded",
            #         "rpc": self.name,
            #         "weight_before": before,
            #         "weight_after": self.current_weight,
            #     },
            # )
       
    def acquire_key(self, batch_mgr: BatchKeyManager | None, max_wait=2.0, sleep_step=0.05):
        """
        Acquire an RPC key for this request.

        Semantics:
        - no key_slots        -> public RPC
        - single key_slot    -> always usable
        - multiple key_slots -> rate-limited round-robin
        """
        # public RPC
        if not self.key_slots:
            return self.base_url, None

        # RPC with single key, no slot
        if len(self.key_slots) == 1:
            slot = self.key_slots[0]
            
            if batch_mgr and not batch_mgr.try_acquire(slot.key_env):
                raise RpcKeyUnavailable(
                    f"Key already used in this batch: {slot.key_env}"
                )
                
            api_key = os.getenv(slot.key_env)
            
            if not api_key:
                raise RuntimeError(
                    f"Missing env var for RPC provider {self.name}: {slot.key_env}"
                )
            return f"{self.base_url}/{api_key}", slot
        
        # multiply key provider：slot + min_interval
        deadline = time.time() + max_wait

        while time.time() < deadline:
            for _ in range(len(self.key_slots)):
                slot = self.key_slots[self._key_cursor]
                self._key_cursor = (self._key_cursor + 1) % len(self.key_slots)

                if slot.try_acquire():
                    if batch_mgr:
                        if not batch_mgr.try_acquire(slot.key_env):
                            slot.release()
                            continue  # 🚫 本 batch 已用过这个 key
                        
                    api_key = os.getenv(slot.key_env)
                    if not api_key:
                        continue

                    return f"{self.base_url}/{api_key}", slot

            time.sleep(sleep_step)

        raise RpcKeyUnavailable(f"No available RPC key for provider={self.name}")

    
class RpcKeyUnavailable(Exception):
    pass

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
    
    def get_provider(self, name: str):
        for p in self.providers:
            if p.name == name:
                return p
        return None

    # ⭐ 工厂方法
    @classmethod
    def from_config(cls, rpc_configs: dict, chain: str) -> "RpcPool":
        chain_cfg = rpc_configs.get("chains", {}).get(chain)
        if not chain_cfg:
            raise RuntimeError(f"Chain config not found: {chain}")

        providers = []

        for cfg in chain_cfg.get("providers", []):
            if not cfg.get("enabled", True):
                continue

            providers.append(
                RpcProvider(
                    name=cfg["name"],
                    base_url=cfg["base_url"],
                    weight=int(cfg.get("weight", 1)),
                    key_env=cfg.get("api_key_env"),  # 保留 list
                )
            )

        if not providers:
            raise RuntimeError(f"No RPC providers enabled for chain: {chain}")

        for p in providers:
            log.info(
                "rpc_enabled",
                extra={
                    "chain": chain,
                    "rpc": p.name,
                    "key_envs": (
                        p.key_env if isinstance(p.key_env, list)
                        else [p.key_env] if p.key_env else ["public"]
                    ),
                    "weight": p.base_weight,
                },
            )

        return cls(providers)



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

        self.consecutive_failures = 0
        self.last_provider: RpcProvider | None = None
        self.batch_key_mgr: BatchKeyManager | None = None


    def begin_batch(self):
        """
        Called once per batch (before concurrent fetch).
        """
        self.batch_key_mgr = BatchKeyManager()

        # log.info(
        #     "🔁 batch_key_scope_begin",
        #     extra={"chain": self.chain},
        # )

    def end_batch(self):
        """
        Called once per batch (after commit).
        """
        if self.batch_key_mgr:
            self.batch_key_mgr.reset()
            self.batch_key_mgr = None

        # log.info(
        #     "✅ batch_key_scope_end",
        #     extra={"chain": self.chain},
        # )

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

            self.last_provider = provider
            
            try:
                url, slot = provider.acquire_key(batch_mgr=self.batch_key_mgr)
            except RpcKeyUnavailable:
                # “资源忙”，不是失败
                # log.info(
                #     "⏳ rpc_key_busy",
                #     extra={
                #         "chain": self.chain,
                #         "rpc": provider.name,
                #     },
                # )
                RPC_KEY_BUSY.labels(chain=self.chain,rpc=provider.name).inc()

                continue  # 🚀 直接换下一个 provider            
                        
            key_env_label = slot.key_env if slot else "public"
            
            RPC_REQUESTS.labels(
                chain=self.chain,
                rpc=provider.name,
                key_env=key_env_label,
            ).inc() # 在原有基础上累加, 只能单调递增, Prometheus 会自动算 rate / increase

            ACTIVE_RPC_CONNECTIONS.labels(
                chain=self.chain,
                rpc=provider.name,
            ).inc()

            w3 = Web3(
                Web3.HTTPProvider(
                    url,
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
                #         "chain": self.chain,
                #         "rpc": provider.name,
                #         "current_weight": provider.current_weight,
                #         "base_weight": provider.base_weight,
                #         "cooldown": not provider.available(),
                #     },
                # )
                
#                | 字段                    | 含义                     |
#                | ----------------------- | -------------------------|
#                | provider.key_env        | 这个 RPC 拥有哪些 key     |
#                | acquire_key() → key_env | 这一次 call 实际使用的 key |

                
                if return_provider:
                    return result, RpcContext(
                        rpc=provider.name,
                        key_env=key_env_label, # 本次 acquire_key() 真正用到的,
                    )
                return result

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
                continue

            # RPC success, RPC timeout, SSLEOF, any Exception → failover
            finally:
                ACTIVE_RPC_CONNECTIONS.labels(
                    chain=self.chain,
                    rpc=provider.name,
                ).dec()
                
                if slot:
                    slot.release()

        # ❌ 本轮全部失败
        self.consecutive_failures += 1
        backoff = min(5 * self.consecutive_failures, self.max_backoff)

        log.error(
            "❌rpc_round_failed",
            extra={
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
        provider = self.last_provider
        if not provider:
            return

        cooldown = seconds or self.penalize_seconds

        provider.penalize(cooldown)

        log.info(
            "rpc_rotated",
            extra={
                "event": "rpc_rotated",
                "chain": self.chain,
                "rpc": provider.name,
                "key_env": provider.key_env,
                "cooldown_seconds": cooldown,
            },
        )