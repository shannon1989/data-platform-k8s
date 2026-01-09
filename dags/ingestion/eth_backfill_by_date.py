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
    - Trigger example: {"start_date": "2026-01-01","end_date": "2026-01-01"}
- 0.1.4:
    - add PythonOperator for input parameter validation
    - input paramter: start_date and end_date (validate first)
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
    dag_id="eth_backfill_by_date",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["eth-mainnet", "KubernetesPodOperator"],
    doc_md = doc_md,
) as dag:
    
    # --------------------------
    # Step1: validate start_date and end_date
    # --------------------------
    def validate_dates(**context):
        dag_run = context.get("dag_run")
        conf = dag_run.conf or {}

        start_date_str = conf.get("start_date")
        end_date_str = conf.get("end_date")

        if not start_date_str or not end_date_str:
            raise AirflowFailException("start_date and end_date are required")

        # validate format YYYY-MM-DD
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise AirflowFailException(f"start_date '{start_date_str}' is not in YYYY-MM-DD format")

        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise AirflowFailException(f"end_date '{end_date_str}' is not in YYYY-MM-DD format")

        # validate start_date <= end_date
        if start_date > end_date:
            raise AirflowFailException("start_date must be less than or equal to end_date")

        return {"start_date": str(start_date), "end_date": str(end_date)}

    validate_date_task = PythonOperator(
        task_id="validate_dates",
        python_callable=validate_dates,
    )

    # --------------------------
    # Step2: run backfill in KubernetesPodOperator
    # --------------------------
    run_backfill_task = KubernetesPodOperator(
        task_id=f"run_{dag.dag_id}",
        name="eth-backfill-date",
        namespace="airflow",
        image="eth-backfill:0.1.3",
        cmds=["python", "eth_backfill_job.py"],
        get_logs=True,
        is_delete_operator_pod=True,
        secrets=[eth_infura_secret, etherscan_secret],
        env_vars={
            # Airflow auto generated run_id
            "JOB_NAME": (
                "{{ dag.dag_id }}"
                "_{{ dag_run.conf.get('start_date') }}"
                "_{{ dag_run.conf.get('end_date') }}"
            ),
            "RUN_ID": "{{ run_id }}",
            "START_DATE": "{{ dag_run.conf.get('start_date') }}",
            "END_DATE": "{{ dag_run.conf.get('end_date') }}",
        },
    )
    
    validate_date_task >> run_backfill_task