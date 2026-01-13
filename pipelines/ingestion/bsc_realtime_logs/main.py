from prometheus_client import start_http_server
from logging import log
from metrics import *
from time_utils import current_utctime
from rpc_provider import RpcProvider, RpcPool, Web3Router
from web3_utils import fetch_block_logs, to_json_safe
from kafka_utils import init_producer, get_serializers
from fetch_push_loop import fetch_and_push
from state import resolve_start_block
import os, uuid, json

# -----------------------------
# Env & Config
# -----------------------------
JOB_NAME = "bsc_realtime" + "_" + current_utctime()
RUN_ID = str(uuid.uuid4())
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "1"))

TRANSACTIONAL_ID = f"blockchain.ingestion.bsc.{JOB_NAME}"
KAFKA_BROKER = "redpanda.kafka.svc:9092"
SCHEMA_REGISTRY_URL = "http://redpanda.kafka.svc:8081"
BLOCKS_TOPIC = "blockchain.logs.bsc"
STATE_TOPIC = "blockchain.state.bsc"

producer = init_producer(TRANSACTIONAL_ID, KAFKA_BROKER)
blocks_value_serializer, state_value_serializer = get_serializers(SCHEMA_REGISTRY_URL, BLOCKS_TOPIC, STATE_TOPIC)

# -----------------------------
# RPC Pool
# -----------------------------
RPC_CONFIG_PATH = "/etc/ingestion/rpc_providers.json"
with open(RPC_CONFIG_PATH) as f:
    rpc_configs = json.load(f)

def build_rpc_pool(rpc_configs):
    providers = []
    for cfg in rpc_configs:
        if not cfg.get("enabled", True):
            continue
        url = cfg["url_template"].format(**os.environ)
        providers.append(RpcProvider(name=cfg["name"], url=url, weight=cfg.get("weight",1)))
    if not providers:
        raise RuntimeError("No RPC providers configured")
    return RpcPool(providers)

rpc_pool = build_rpc_pool(rpc_configs)
web3_router = Web3Router(rpc_pool)

# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    start_http_server(8000)
    fetch_and_push(
        JOB_NAME, RUN_ID, web3_router, producer,
        blocks_value_serializer, state_value_serializer,
        BATCH_SIZE, POLL_INTERVAL,
        BLOCKS_TOPIC, STATE_TOPIC
    )
