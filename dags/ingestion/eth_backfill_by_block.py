from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException
import subprocess
import os
import socket
from datetime import datetime

@dag(
    dag_id="eth_backfill_by_block",
    start_date=datetime(2024, 3, 27),
    schedule=None,           # triger manually
    catchup=False,
    tags=["eth", "backfill", "block"],
)
def eth_backfill_by_block():

    @task
    def run_backfill(**context):
        dag_run = context["dag_run"]

        conf = dag_run.conf or {}
        start_block = conf.get("start_block")
        end_block = conf.get("end_block")

        # Trigger from UI
        # {
        # "start_block": 24188501,
        # "end_block": 24188600
        # }
        
        if not start_block or not end_block:
            raise AirflowFailException("start_block and end_block are required")

        env = os.environ.copy()
        env.update({
            "RUN_ID": dag_run.run_id,
            "JOB_NAME": "eth_backfill",
            "START_BLOCK": int(start_block),
            "END_BLOCK": int(end_block),
        })

        cmd = [
            "python",
            "/opt/airflow/dags/repo/pipelines/ingestion/eth_backfill_job.py"
        ]

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            raise AirflowFailException("eth_backfill_job failed")

    run_backfill()

dag = eth_backfill_by_block()
