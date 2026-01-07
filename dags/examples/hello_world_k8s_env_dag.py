from __future__ import annotations

import os
import socket
from datetime import datetime

from airflow.decorators import dag, task


def print_runtime_env(task_name: str):
    """
    Print runtime environment information.
    Works for:
    - LocalExecutor
    - KubernetesExecutor
    - K8s Pod (via git-sync DAG)
    """
    print("=" * 60)
    print(f"Task Name        : {task_name}")
    print(f"Hostname         : {socket.gethostname()}")
    print(f"HOSTNAME env     : {os.getenv('HOSTNAME')}")
    print(f"Namespace        : {os.getenv('POD_NAMESPACE')}")
    print(f"Node Name        : {os.getenv('NODE_NAME')}")
    print(f"Pod IP           : {os.getenv('POD_IP')}")
    print(f"Airflow Executor : {os.getenv('AIRFLOW__CORE__EXECUTOR')}")
    print("=" * 60)


@dag(
    dag_id="hello_world_k8s_runtime_env",
    start_date=datetime(2024, 3, 27),
    schedule="@hourly",
    catchup=False,
    tags=["hello", "k8s", "observability"],
)
def hello_world_k8s_runtime_env():
    """
    Print Pod / Host / Executor info for each task.
    """

    @task
    def hello_world():
        print_runtime_env("hello_world")
        print("Hello World")

    @task.bash
    def sleep():
        echo = (
            'echo "==============================================" && '
            'echo "Task Name    : sleep" && '
            'echo "Hostname     : $(hostname)" && '
            'echo "HOSTNAME env : $HOSTNAME" && '
            'echo "Executor     : $AIRFLOW__CORE__EXECUTOR" && '
            'echo "==============================================" && '
            'sleep 10'
        )
        return echo

    @task
    def goodbye_world():
        print_runtime_env("goodbye_world")
        print("Goodbye World")

    @task
    def done():
        print_runtime_env("done")
        print("Done 🎉")

    hello_world() >> sleep() >> goodbye_world() >> done()


hello_world_k8s_runtime_env()
