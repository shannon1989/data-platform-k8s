from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.operators.python import get_current_context
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret
from datetime import datetime

doc_md = """
### eth-backfill

Image: eth-backfill
Changes:
0.1.1: Use KuerbenetesPodOperator
0.1.2: 
    - Add RPC env injection
    - Fix schema registry dependency
    - Insert ENV from k8s secrets
0.1.3:
    - Insert static and dynamic variable
    - Trigger example: {"start_block": 24188501,"end_block": 24188600}
"""

eth_infura_secret = Secret(
    deploy_type="env",
    deploy_target="ETH_INFURA_RPC_URL",
    secret="eth-secrets",
    key="ETH_INFURA_RPC_URL",
)

etherscan_secret = Secret(
    deploy_type="env",
    deploy_target="ETH_ETHERSCAN_API_KEY",
    secret="eth-secrets",
    key="ETH_ETHERSCAN_API_KEY",
)

with DAG(
    dag_id="eth_backfill_by_block",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["eth-mainnet", "backfill", "ingestion"],
    doc_md = doc_md,
) as dag:

    def get_env_vars(**context):
        dag_run = context["dag_run"]
        conf = dag_run.conf or {}

        start_block = conf.get("start_block")
        end_block = conf.get("end_block")

        if not start_block or not end_block:
            raise AirflowFailException("start_block and end_block are required")

        env = {
            "JOB_NAME": "eth_backfill",
            "START_BLOCK": str(start_block),
            "END_BLOCK": str(end_block),
        }
        return env
    
    run_backfill = KubernetesPodOperator(
        task_id="run_eth_backfill_by_block",
        name="eth-backfill",
        namespace="default",
        image="eth-backfill:0.1.2",
        cmds=["python", "eth_backfill_job.py"],
        get_logs=True,
        is_delete_operator_pod=True,
        secrets=[eth_infura_secret, etherscan_secret],
        env_vars=get_env_vars,
    )
