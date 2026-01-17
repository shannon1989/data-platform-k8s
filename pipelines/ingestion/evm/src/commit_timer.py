import time
from collections import defaultdict

class CommitTimer:
    def __init__(self):
        self.last_commit_ts = None
        self.rpc_cost = defaultdict(float)
        self.rpc_calls = defaultdict(int)

    def mark_rpc(self, rpc_name: str, cost: float):
        self.rpc_cost[rpc_name] += cost
        self.rpc_calls[rpc_name] += 1

    def commit_cost(self):
        now = time.time()
        if self.last_commit_ts is None:
            delta = None
        else:
            delta = round(now - self.last_commit_ts, 2)

        self.last_commit_ts = now

        # -----------------------------
        # ⭐ 计算 avg_rpc_cost
        # -----------------------------
        avg_rpc_cost = {}
        rpc_cost_sec = {}
        for rpc_name, total_cost in self.rpc_cost.items():
            calls = self.rpc_calls.get(rpc_name, 0)
            if calls > 0:
                avg_rpc_cost[rpc_name] = round(total_cost / calls, 4)
                rpc_cost_sec[rpc_name] = round(total_cost, 2)

        
        snapshot = {
            "commit_interval_sec": delta,
            "rpc_cost_sec": rpc_cost_sec,
            "rpc_calls": dict(self.rpc_calls),
            "avg_rpc_cost": avg_rpc_cost,
        }

        # reset for next batch
        self.rpc_cost.clear()
        self.rpc_calls.clear()

        return snapshot