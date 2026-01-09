from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret
from datetime import datetime

doc_md = """
### eth-backfill

Image: eth-backfill
Changes:
- 0.1.1: Use KuerbenetesPodOperator
- 0.1.2: 
    - Add RPC env injection
    - Fix schema registry dependency
    - Insert ENV from k8s secrets
- 0.1.3:
    - Insert static and dynamic variable
    - Trigger example: {"start_block": 24188501,"end_block": 24188600}
- 0.1.4:
    - add PythonOperator for input parameter validation
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
    
    # --------------------------
    # Step1: validate start_block and end_block
    # --------------------------
    def validate_blocks(**context):
        dag_run = context.get("dag_run")
        conf = dag_run.conf or {}
        start_block = conf.get("start_block")
        end_block = conf.get("end_block")

        if not start_block or not end_block:
            raise AirflowFailException("start_block and end_block are required")
        if int(end_block) < int(start_block):
            raise AirflowFailException("start_block must less or equal than end_block")

        # return conf for downstream task
        return {"start_block": start_block, "end_block": end_block}

    validate_blocks_task = PythonOperator(
        task_id="validate_blocks",
        python_callable=validate_blocks
    )
    
    # --------------------------
    # Step2: run backfill in KubernetesPodOperator
    # --------------------------
    run_backfill_task = KubernetesPodOperator(
        task_id="run_eth_backfill_by_block",
        name="eth-backfill-block",
        namespace="airflow",
        image="eth-backfill:0.1.2",
        cmds=["python", "eth_backfill_job.py"],
        get_logs=True,
        is_delete_operator_pod=True,
        secrets=[eth_infura_secret, etherscan_secret],
        env_vars={
            # Airflow auto generated run_id
            "RUN_ID": "{{ run_id }}",
            "START_BLOCK": "{{ dag_run.conf.get('start_block') }}",
            "END_BLOCK": "{{ dag_run.conf.get('end_block') }}",
        },
    )
    
    validate_blocks_task >> run_backfill_task