"""Monthly ELT + data quality for the Berka bank.

  load_files ─────────┐
  load_transactions ──┼─> dbt_build ─> dq_checks ─> reconcile
  load_switch ────────┘

catchup=True replays 1993-01 .. 1998-12 as 72 monthly runs, the way a new pipeline backfills history.
max_active_runs=1 keeps months in order (fact_transactions is incremental on loaded_at).
Every task is idempotent, so clearing and re-running any run is safe. A missing switch file fails
load_switch, Airflow retries it, and the run stays red until the file arrives (timeliness).
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "/opt/project"
PY = "/opt/app/venv/bin/python"
DBT = f"/opt/app/venv/bin/dbt build --profiles-dir {PROJECT}/warehouse --project-dir {PROJECT}/warehouse"
INTERVAL = "{{ data_interval_start | ds }} {{ data_interval_end | ds }}"

with DAG(
    dag_id="bank_pipeline",
    start_date=datetime(1993, 1, 1),
    end_date=datetime(1998, 12, 1),
    schedule="@monthly",
    catchup=True,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=30), "cwd": PROJECT},
    tags=["banking", "elt", "data-quality"],
) as dag:
    load_files = BashOperator(task_id="load_files", bash_command=f"{PY} -m pipeline.cli files")
    load_transactions = BashOperator(task_id="load_transactions",
                                     bash_command=f"{PY} -m pipeline.cli transactions {INTERVAL}")
    load_switch = BashOperator(task_id="load_switch",
                               bash_command=f"{PY} -m pipeline.cli switch {{{{ data_interval_start | ds }}}}")
    dbt_build = BashOperator(task_id="dbt_build", bash_command=DBT)
    dq_checks = BashOperator(task_id="dq_checks", bash_command=f"{PY} -m dq.checks {INTERVAL}")
    reconcile = BashOperator(task_id="reconcile", bash_command=f"{PY} -m dq.reconcile {INTERVAL}")

    [load_files, load_transactions, load_switch] >> dbt_build >> dq_checks >> reconcile
