from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.job import KubernetesJobOperator
from airflow.models import Param
from datetime import datetime

doc_md = """
### eth-backfill

Image: eth-backfill
Changes:
- 0.1.4: Use KuerbenetesJobOperator and insert JOB_NAME from DAG
"""

with DAG(
    dag_id="eth_backfill_k8s_job_by_date",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    params={
        "start_date": Param("2026-01-02", type="string"),
        "end_date": Param("2026-01-02", type="string"),
    },
    tags=["eth-mainnet", "KubernetesJobOperator"],
    doc_md = doc_md,
) as dag:

    run_backfill = KubernetesJobOperator(
        task_id="run_eth_backfill",
        namespace="airflow",

        job_template_file=(
            "/opt/airflow/dags/repo/"
            "dags/k8s/jobs/eth-backfill-job.yaml"
        ),

        # Jinja Job YAML
        params={
            "START_DATE": "{{ params.start_date }}",
            "END_DATE": "{{ params.end_date }}",
            "RUN_ID": "{{ run_id }}",
            "JOB_NAME": "{{ dag.dag_id }}_{{ params.start_date }}_{{ params.end_date }}",
        },
    )

    run_backfill
