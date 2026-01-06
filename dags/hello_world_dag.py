from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime
from airflow.decorators import dag, task
from kubernetes.client import models as k8s


default_executor_config = {
    "pod_override": k8s.V1Pod(
        spec=k8s.V1PodSpec(
            containers=[
                k8s.V1Container(
                    name="base",
                    resources=k8s.V1ResourceRequirements(
                        requests={"cpu": "100m", "memory": "128Mi"},
                        limits={"cpu": "200m", "memory": "256Mi"}
                    )
                )
            ]
        )
    )
} # end of default_executor_config

with DAG(dag_id="hello_world_dag",
         start_date=datetime(2024,3,27),
         schedule="@hourly",
         catchup=False) as dag:

    @task(
        task_id="hello_world",
        executor_config=default_executor_config
    )
    def hello_world():
        print('Hello World - From Github Repository')



    @task.bash(
        task_id="sleep",
    )
    def sleep_task() -> str:
        return "sleep 10"


    @task(
        task_id="done",
        #executor_config=default_executor_config
    )
    def done():
        print('Done')


    @task(
        task_id="goodbye_world",
    )
    def goodbye_world():
        print('Goodbye World - From Github Repository')


    hello_world_task = hello_world()
    sleep_task = sleep_task()
    goodbye_world_task = goodbye_world()
    done_task = done()


    hello_world_task >> sleep_task >> goodbye_world_task >> done_task