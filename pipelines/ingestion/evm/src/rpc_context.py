# rpc_context.py
import threading

_rpc_ctx = threading.local()

def set_current_rpc(name):
    _rpc_ctx.name = name

def get_current_rpc():
    return getattr(_rpc_ctx, "name", "unknown")
