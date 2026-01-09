from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret
from datetime import datetime

doc_md = """
### eth-backfill

Image: eth-backfill:0.1.2  
Changes:
- Add RPC env injection
- Fix schema registry dependency
"""


eth_secret = Secret(
    deploy_type="env",
    deploy_target="ETH_INFURA_RPC_URL",
    secret="eth-secrets",
    key="ETH_INFURA_RPC_URL",
)

with DAG(
    dag_id="eth_backfill_k8s_pod",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    run_backfill = KubernetesPodOperator(
        task_id="run_eth_backfill",
        name="eth-backfill",
        namespace="default",
        image="eth-backfill:0.1.2",
        cmds=["python", "eth_backfill_job.py"],
        get_logs=True,
        is_delete_operator_pod=True,
        # secrets=[eth_secret], # insert k8s secrets
    )
