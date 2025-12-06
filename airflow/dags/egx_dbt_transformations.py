"""
EGX dbt Transformations DAG

Daily batch job to run dbt transformations on EGX market data.
Reads data from S3, transforms through Bronze → Silver → Gold layers,
and loads into Snowflake for analytics.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os

# Get project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

default_args = {
    'owner': 'egx-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 6),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

with DAG(
    'egx_dbt_transformations',
    default_args=default_args,
    description='Daily dbt transformations: S3 → Snowflake (Bronze/Silver/Gold)',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    catchup=False,
    max_active_runs=1,
    tags=['egx', 'dbt', 'batch', 'analytics'],
) as dag:

    # Activate virtual environment
    venv_activate = f"source {PROJECT_ROOT}/.venv/bin/activate && "

    # Task 1: Load S3 data to Snowflake Bronze layer
    load_bronze = BashOperator(
        task_id='load_s3_to_bronze',
        bash_command=(
            f"{venv_activate}"
            f"python {PROJECT_ROOT}/sql/run_sql.py "
            f"{PROJECT_ROOT}/sql/05_load_s3_to_bronze.sql"
        ),
        execution_timeout=timedelta(minutes=30),
    )

    # Task 2: Run dbt models (Bronze → Silver → Gold)
    dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command=(
            f"{venv_activate}"
            f"cd {PROJECT_ROOT}/egx_dw && "
            f"dbt run --profiles-dir ~/.dbt"
        ),
        execution_timeout=timedelta(minutes=20),
    )

    # Task 3: Run dbt tests (data quality)
    dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command=(
            f"{venv_activate}"
            f"cd {PROJECT_ROOT}/egx_dw && "
            f"dbt test --profiles-dir ~/.dbt"
        ),
        execution_timeout=timedelta(minutes=10),
    )

    # Task 4: Generate dbt documentation
    dbt_docs = BashOperator(
        task_id='dbt_docs',
        bash_command=(
            f"{venv_activate}"
            f"cd {PROJECT_ROOT}/egx_dw && "
            f"dbt docs generate --profiles-dir ~/.dbt"
        ),
        execution_timeout=timedelta(minutes=5),
    )

    # Pipeline flow
    load_bronze >> dbt_run >> dbt_test >> dbt_docs
