from __future__ import annotations

from datetime import datetime

from airflow.decorators import dag, task


@dag(
    dag_id="hello_world_dag",
    start_date=datetime(2024, 3, 27),
    schedule="@hourly",
    catchup=False,
    tags=["example"],
)
def hello_world_dag():
    """
    A minimal, production-safe Hello World DAG for Airflow 3 on Kubernetes.

    - TaskFlow API
    - No executor-specific config
    - Safe for LocalExecutor / KubernetesExecutor
    """

    @task
    def hello_world():
        print("Hello World - From Git-Synced Repository")

    @task.bash
    def sleep():
        return "sleep 10"

    @task
    def goodbye_world():
        print("Goodbye World")

    @task
    def done():
        print("Done 🎉")

    # Task dependencies
    hello_world() >> sleep() >> goodbye_world() >> done()


# DAG object
hello_world_dag()
