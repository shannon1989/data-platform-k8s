from airflow import DAG
from datetime import datetime
from airflow.providers.cncf.kubernetes.operators.job import KubernetesJobOperator

with DAG(
    dag_id="eth_backfill_k8s_job",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    create_job = KubernetesJobOperator(
      task_id="create_eth_backfill_job",
      namespace="default",
      job_template_file="/opt/airflow/jobs/eth-backfill-job.yaml",
  )

    create_job