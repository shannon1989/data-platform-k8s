# 文件名: test_r2_log_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

def hello_world():
    print("Hello R2! This log should go to Cloudflare R2.")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="test_r2_log_dag",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval=None,  # 手动触发
    catchup=False,
    tags=["test", "r2"],
) as dag:

    task1 = PythonOperator(
        task_id="print_hello",
        python_callable=hello_world
    )

    task1