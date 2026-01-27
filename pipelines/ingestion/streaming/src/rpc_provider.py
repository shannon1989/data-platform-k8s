import os
import time
import random
import asyncio
import aiohttp
import uuid
from dataclasses import dataclass
from typing import NamedTuple
import itertools
from src.logging import log
from src.web3_utils import build_method_group_map
from src.metrics.runtime import get_metrics

_m = None
def m():
    global _m
    if _m is None:
        _m = get_metrics()
    return _m

# -----------------------------
# Exceptions
# -----------------------------
class RpcKeyUnavailable(Exception): pass
class RpcTemporarilyUnavailable(Exception): pass
class RpcRateLimitError(Exception): pass

# -----------------------------
# RPC Trace
# -----------------------------
@dataclass
class RpcTrace:
    method: str
    dns_ms: float | None = None
    tcp_ms: float | None = None
    http_wait_ms: float | None = None
    total_ms: float | None = None

@dataclass
class RpcTaskMeta:
    task_id: int
    submit_ts: float
    extra: dict

@dataclass
class RpcErrorResult:
    error: Exception
    rpc: str | None
    key_env: str | None
    meta: RpcTaskMeta
    wid: int


# -----------------------------
# AsyncRpcClient
# 发送 JSON-RPC，量所有网络阶段，返回 (result, trace)
# -----------------------------
class AsyncRpcClient:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _build_trace_config(self, trace: RpcTrace):
        tc = aiohttp.TraceConfig()

        async def on_dns_start(_, __, ___):
            trace._dns_start = time.perf_counter()

        async def on_dns_end(_, __, ___):
            trace.dns_ms = (time.perf_counter() - trace._dns_start) * 1000

        async def on_connection_create_start(_, __, ___):
            trace._tcp_start = time.perf_counter()

        async def on_connection_create_end(_, __, ___):
            trace.tcp_ms = (time.perf_counter() - trace._tcp_start) * 1000

        async def on_request_headers_sent(_, __, ___):
            trace._http_wait_start = time.perf_counter()

        async def on_response_chunk_received(_, __, ___):
            if trace.http_wait_ms is None:
                trace.http_wait_ms = (
                    time.perf_counter() - trace._http_wait_start
                ) * 1000

        tc.on_dns_resolvehost_start.append(on_dns_start)
        tc.on_dns_resolvehost_end.append(on_dns_end)
        tc.on_connection_create_start.append(on_connection_create_start)
        tc.on_connection_create_end.append(on_connection_create_end)
        tc.on_request_headers_sent.append(on_request_headers_sent)
        tc.on_response_chunk_received.append(on_response_chunk_received)

        return tc

    async def call(self, url: str, method: str, params: list):
        trace = RpcTrace(method=method)
        trace_cfg = self._build_trace_config(trace)

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }

        # 禁用 brotli，避免 aiohttp / brotli 兼容问题
        RPC_HEADERS = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }

        start = time.perf_counter()
        async with aiohttp.ClientSession(
            timeout=timeout,
            trace_configs=[trace_cfg],
        ) as session:
            async with session.post(url,
                json=payload,
                headers=RPC_HEADERS
                ) as resp:
                if resp.status == 429:
                    raise RpcRateLimitError("HTTP 429 rate limited")
                data = await resp.json()

        trace.total_ms = (time.perf_counter() - start) * 1000

        if "error" in data:
            code = data["error"].get("code")
            if code in (-32005, -32016, -32000, 10007):
                raise RpcRateLimitError(data["error"])
            raise RuntimeError(data["error"])

        return data["result"], trace


# -----------------------------
# RpcContext
# -----------------------------
class RpcContext(NamedTuple):
    rpc: str
    key_env: str

# -----------------------------
# RPC Key Slot: 滑动窗口频率控制
# -----------------------------
class RpcKeySlot:
    def __init__(self, key_env: str, min_interval: float):
        self.key_env = key_env
        self.min_interval = min_interval
        self._lock = asyncio.Lock()
        self._next_available = 0.0

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            if now < self._next_available:
                m().rpc_key_unavailable_inc(self.key_env)
                raise RpcKeyUnavailable(self.key_env)

            self._next_available = now + self.min_interval
            return os.getenv(self.key_env)

# -----------------------------
# RPC Provider
# -----------------------------
class RpcProvider:
    def __init__(self, name, base_url, weight, key_envs=None, key_interval=1.0):
        self.name = name
        self.base_url = base_url
        self.weight = weight
        
        # Circuit breaker state
        self.cooldown_until = 0.0
        self.fail_count = 0
        self.fail_threshold = 3           # 连续失败 3 次触发熔断, 避免偶发网络抖动
        self.cooldown_sec = 10            # 熔断冷却时间
        self.half_open_probe = False      # HALF_OPEN 探测锁, 确保冷却后只有一个请求能试探

        # normalize key_envs: None | str | list -> list
        if not key_envs:
            self.key_envs = []
        elif isinstance(key_envs, str):
            self.key_envs = [key_envs]
        else:
            self.key_envs = list(key_envs)
    
        self.slots = [
            RpcKeySlot(env, key_interval)
            for env in self.key_envs
        ]

        self._rr = 0

    def available(self):
        now = time.monotonic()

        # OPEN 状态：还在冷却
        if now < self.cooldown_until:
            return False

        # 冷却结束 → HALF_OPEN
        if self.cooldown_until > 0 and not self.half_open_probe:
            log.info(
                "⚠️ rpc_half_open_probe",
                extra={
                    "rpc": self.name,
                },
            )
            self.half_open_probe = True
            return True

        # CLOSED 或 HALF_OPEN 已被占用
        return self.cooldown_until == 0

    def on_success(self):
        # HALF_OPEN 成功 → CLOSED
        self.fail_count = 0
        self.cooldown_until = 0.0
        self.half_open_probe = False

    def on_failure(self, cooldown: float | None = None):
        self.fail_count += 1

        if self.fail_count >= self.fail_threshold:
            cd = cooldown or self.cooldown_sec
            self.cooldown_until = time.monotonic() + cd
            self.half_open_probe = False
            log.warning(
                "⚠️ rpc_circuit_open",
                extra={
                    "rpc": self.name,
                    "cooldown_sec": cd,
                    "fail_count": self.fail_count,
                },
            )


    def on_half_open_failure(self):
        # HALF_OPEN 探测失败 → 立刻回 OPEN
        self.cooldown_until = time.monotonic() + self.cooldown_sec
        self.half_open_probe = False
        

    async def acquire_slot(self):
        if not self.slots:
            return self.base_url, "public"

        for _ in range(len(self.slots)):
            slot = self.slots[self._rr]
            self._rr = (self._rr + 1) % len(self.slots)
            try:
                key = await slot.acquire()
                return f"{self.base_url}/{key}", slot.key_env
            except RpcKeyUnavailable:
                continue

        raise RpcKeyUnavailable(self.name)



# -----------------------------
# RpcPool
# -----------------------------
class RpcPool:
    def __init__(self, providers):
        self.providers = providers
        
    def pick_providers(self):
        """
        根据 weight 生成一个 provider 尝试顺序 (weight越大, 越先尝试这个provider)
        """
        candidates = []

        for p in self.providers:
            if not p.available():
                continue
            candidates.extend([p] * p.weight)

        random.shuffle(candidates)
        return candidates
    
    @classmethod
    def grouped_from_config(cls, rpc_configs: dict, chain: str) -> "GroupedRpcPool":
        chain_cfg = rpc_configs["chains"][chain]
    
        method_group_map = build_method_group_map(chain_cfg)
    
        pools: dict[str, RpcPool] = {}
    
        for cfg in chain_cfg.get("providers", []):
            if not cfg.get("enabled", True):
                continue
    
            groups = cfg.get("method_groups", [])
            if isinstance(groups, str):
                groups = [groups]
    
            for g in groups:
                pools.setdefault(g, []).append(
                    RpcProvider(
                        name=cfg["name"],
                        base_url=cfg["base_url"],
                        weight=int(cfg.get("weight", 1)),
                        key_envs=cfg.get("api_keys_env"),
                        key_interval=float(cfg.get("key_interval", 1.0)),
                    )
                )
    
        rpc_pools = {
            g: RpcPool(providers)
            for g, providers in pools.items()
        }
    
        return GroupedRpcPool(rpc_pools, method_group_map)


# 按 method_group 构建多个 RpcPool
class GroupedRpcPool:
    def __init__(self, pools: dict[str, RpcPool], method_group_map: dict[str, str]):
        self.pools = pools
        self.method_group_map = method_group_map

    def pool_for_method(self, method: str) -> RpcPool:
        group = self.method_group_map.get(method)
        if not group:
            log.warning("method_group_not_found", extra={"method": method})
            group = "heavy"

        pool = self.pools.get(group)
        if not pool:
            raise RuntimeError(f"No RPC pool for method_group: {group}")

        return pool


class Web3AsyncRouter:
    def __init__(self, grouped_pool: GroupedRpcPool, client):
        self.grouped_pool = grouped_pool
        self.client = client

    async def call_once(self, method, params):
        pool = self.grouped_pool.pool_for_method(method)
        providers = pool.pick_providers()

        for p in providers:
            if not p.available():
                continue

            try:
                url, key_env = await p.acquire_slot()
            except RpcKeyUnavailable:
                continue

            try:
                result, trace = await self.client.call(url, method, params)
                
                p.on_success()
                return result, p.name, key_env, trace

            except RpcRateLimitError as e:
                p.on_failure(cooldown=30)   # 强熔断
                continue   # 尝试下一个 provider

            except (TimeoutError, asyncio.TimeoutError):
                p.on_failure()              # 计数，但不拉长 cooldown
                continue   # 尝试下一个 provider

            # except RuntimeError as e:
            #     # code == 19 / temporary error → 弱熔断
                
            #     p.on_failure(cooldown=10)   # 冷却10s
            #     log.warning("⚠️ rpc_runtime_error",
            #             extra={
            #             "provider":p.name,
            #             "key": key_env,
            #             "error_type": type(e).__name__,
            #             "error": str(e)},
            #             )
            #     raise

            except Exception as e:
                m().rpc_failed_inc(provider=p.name, key=key_env)
                
                log.warning("⚠️ rpc_call_error",
                        extra={
                        "provider":p.name,
                        "key": key_env,
                        "error_type": type(e).__name__,
                        "error": str(e)},
                        )
                
                if p.half_open_probe:
                    p.on_half_open_failure()
                else:
                    p.on_failure(cooldown=10) # 冷却10s
                raise

        raise RpcTemporarilyUnavailable()


    async def get_latest_block(self) -> int:
        result, rpc, key_env, trace = await self.call_once(
            "eth_blockNumber",
            []
        )
        log.info(
            "📦 get_latest_block",
            extra={
                "rpc": rpc,
                "key_env": key_env,
                "method": "eth_blockNumber",
                "latest_block": int(result, 16)
            },
        )
        return int(result, 16)


_task_seq = itertools.count(1)
_STOP = object()

class AsyncRpcScheduler:
    def __init__(
        self,
        router,
        max_workers: int,
        max_queue: int,
        max_inflight: int,
    ):
        self.router = router
        self.queue = asyncio.Queue(max_queue)
        self.inflight = asyncio.Semaphore(max_inflight)
        self.workers = []
        self._closed = False

        for wid in range(max_workers):
            task = asyncio.create_task(self._dispatcher_loop(wid))
            self.workers.append(task)

    async def submit(
        self,
        method: str, 
        params: list,
        *,
        meta: dict | None = None,
    ):
        if self._closed:
            raise RuntimeError("Scheduler already closed")

        loop = asyncio.get_running_loop()
        fut = loop.create_future()

        task_meta = RpcTaskMeta(
            task_id=next(_task_seq),
            submit_ts=time.time(),
            extra=meta or {},   # 🔥 业务 meta
        )

        await self.queue.put((method, params, fut, task_meta))

        m().rpc_submitted_inc()
        m().rpc_queue_size_set(self.queue.qsize())
        
        return await fut

    async def _dispatcher_loop(self, wid: int):
        log.info("rpc_dispatcher_started", extra={"worker": wid})

        while True:
            try:
                item = await self.queue.get()

                # 🔥 关键：收到退出信号
                if item is _STOP:
                    self.queue.task_done()
                    break
                
                method, params, fut, meta = item
            except asyncio.CancelledError:
                break

            dispatch_ts = time.time()

            queue_wait_ms = (dispatch_ts - meta.submit_ts) * 1000
            m().rpc_queue_wait_observe(queue_wait_ms)
            m().rpc_queue_size_set(self.queue.qsize())
            
            # log.info(
            #     "rpc_dispatch",
            #     extra={
            #         "task_id": meta.task_id,
            #         # "worker": wid,
            #         "method": method,
            #         "queue_wait_ms": round(
            #             (dispatch_ts - meta.submit_ts) * 1000, 2
            #         ),
            #     },
            # )

            # 🔥 不 await RPC
            asyncio.create_task(
                self._execute_rpc(method, params, fut, meta, wid)
            )

            self.queue.task_done()

    async def _execute_rpc(self, method, params, fut, meta, wid):
        async with self.inflight:
            # rpc_start_ts = time.time()

            m().rpc_started.inc()
            m().rpc_inflight.inc()
            
            # log.info(
            #     "rpc_call_start",
            #     extra={
            #         "task_id": meta.task_id,
            #         # "worker": wid,
            #         "method": method,
            #     },
            # )

            try:
                result, rpc, key_env, trace = await self.router.call_once(
                    method, params
                )
                
                m().rpc_completed_inc(rpc, key_env)
                
                if trace and trace.total_ms is not None:
                    # key 级别的问题 用 Counter 看，延迟分布 只看 provider 级
                    m().rpc_latency_observe(rpc, trace.total_ms)
                    
                if not fut.done():
                    fut.set_result(
                        (result, rpc, key_env, trace, wid, meta)
                    )

                # log.info(
                #     "rpc_call_done",
                #     extra={
                #         "task_id": meta.task_id,
                #         # "worker": wid,
                #         "rpc": rpc,
                #         "key_env": key_env,
                #         "latency_ms": round(
                #             (time.time() - rpc_start_ts) * 1000, 2
                #         ),
                #     },
                # )

            except Exception as e:
                # log.warning(
                #     "⚠️ rpc_call_error",
                #     extra={
                #         "task_id": meta.task_id,
                #         # "worker": wid,
                #         "error_type": type(e).__name__,
                #         "error": str(e),
                #     },
                # )
            
                if not fut.done():
                    fut.set_result(
                        RpcErrorResult(
                            error=e,
                            rpc=None,
                            key_env=None,
                            meta=meta,
                            wid=wid,
                        )
                    )
            finally:
                m().rpc_inflight.dec()
                m().rpc_finished_inc()


    async def close(self):
        if self._closed:
            return
    
        self._closed = True
    
        # 等待所有 submit 的任务被 dispatcher 消化
        await self.queue.join()
    
        # 给 dispatcher 发退出信号
        for _ in self.workers:
            await self.queue.put(_STOP)
    
        # 等 dispatcher 正常退出
        await asyncio.gather(*self.workers, return_exceptions=True)
