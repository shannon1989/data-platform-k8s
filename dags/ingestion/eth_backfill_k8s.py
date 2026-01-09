from airflow import DAG
from datetime import datetime
from airflow.providers.cncf.kubernetes.operators.kubernetes_job import KubernetesJobOperator

with DAG(
    dag_id="eth_backfill_k8s_with_progress",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    create_job = KubernetesJobOperator(
      task_id="create_eth_backfill_job",
      job_name="eth-backfill-job",
      namespace="default",
      image="eth-backfill:0.1.0",
      cmds=["python", "eth_backfill_job.py"],
  )

    monitor = KafkaProgressSensor(
        task_id="monitor_progress",
        job_name="eth_backfill",
        poke_interval=10,
        timeout=60 * 60,
    )

    create_job >> monitor