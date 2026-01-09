from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from datetime import datetime

with DAG(
    dag_id="eth_backfill_k8s",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    run_backfill = KubernetesPodOperator(
        task_id="run_eth_backfill",
        name="eth-backfill",
        namespace="default",
        image="eth-backfill:0.1.0",
        cmds=["python", "eth_backfill_job.py"],
        get_logs=True,
        is_delete_operator_pod=True,
    )
