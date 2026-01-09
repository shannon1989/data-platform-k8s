from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.job import KubernetesJobOperator
from airflow.models import Param
from datetime import datetime
from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator

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

    # --------------------------
    # Step1: validate start_date and end_date
    # --------------------------
    def validate_dates(**context):
        params = context["params"]
        start_date_str = params["start_date"]
        end_date_str = params["end_date"]

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
    
    run_backfill_task = KubernetesJobOperator(
        task_id=f"run_{dag.dag_id}",
        namespace="airflow",
        
        labels={
            "job": "eth-backfill",
            "chain": "eth-mainnet",
        },

        job_template_file=("/opt/airflow/dags/repo/dags/k8s/jobs/eth-backfill-job.yaml"),
        
        # Airflow business parameter ingestion (Jinja)
        env_vars={
            "START_DATE": "{{ params.start_date }}",
            "END_DATE": "{{ params.end_date }}",
            "RUN_ID": "{{ run_id }}",
            "JOB_NAME": (
                "{{ dag.dag_id }}"
                "_{{ params.start_date }}"
                "_{{ params.end_date }}"
            ),
        },
        retries=1,
        retry_delay=timedelta(minutes=5),
        execution_timeout=timedelta(hours=6),
        wait_until_job_complete=True,
    )

    validate_date_task >> run_backfill_task
