@dag(
    dag_id="eth_backfill_by_date",
    start_date=days_ago(1),
    schedule=None,
    catchup=False,
    tags=["eth", "backfill", "date"],
)
def eth_backfill_by_date():

    @task
    def run_backfill(**context):
        dag_run = context["dag_run"]
        conf = dag_run.conf or {}

        start_date = conf.get("start_date")
        end_date = conf.get("end_date")

        if not start_date or not end_date:
            raise AirflowFailException("start_date and end_date are required")

        env = os.environ.copy()
        env.update({
            "RUN_ID": dag_run.run_id,
            "JOB_NAME": "eth_backfill",
            "START_DATE": start_date,
            "END_DATE": end_date,
        })

        result = subprocess.run(
            ["python", "/home/jovyan/work/jobs/eth_backfill_job.py"],
            env=env,
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            raise AirflowFailException("eth_backfill_job failed")

    run_backfill()

dag = eth_backfill_by_date()
