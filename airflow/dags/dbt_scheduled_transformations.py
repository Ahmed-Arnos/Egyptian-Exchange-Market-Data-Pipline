"""
DBT Scheduled Transformations DAG
---------------------------------
Runs dbt transformations twice daily to keep analytics data up to date.
This DAG focuses solely on running dbt models without batch processing.

Schedule: Runs at 2 AM and 2 PM Cairo time (00:00 and 12:00 UTC)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import os

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email': ['ahmed@example.com'],  # Update with your email
}

# Define the DAG
dag = DAG(
    'dbt_scheduled_transformations',
    default_args=default_args,
    description='Run dbt transformations twice daily for Egyptian Exchange data',
    schedule_interval='0 0,12 * * *',  # Run at midnight and noon UTC (2 AM and 2 PM Cairo)
    start_date=datetime(2025, 12, 9),
    catchup=False,
    tags=['dbt', 'analytics', 'transformations', 'egyptian-exchange'],
)

# Define dbt parameters - adjust paths as needed
DBT_PROJECT_DIR = os.getenv('DBT_PROJECT_DIR', '/home/ahmed-elsaba/Git Repos/Egyptian-Exchange-Market-Data-Pipline/egx_dw')
DBT_VENV_ACTIVATE = 'source /home/ahmed-elsaba/Git Repos/Egyptian-Exchange-Market-Data-Pipline/.venv-aws/bin/activate'
DBT_ENV_EXPORT = 'export $(cat /home/ahmed-elsaba/Git Repos/Egyptian-Exchange-Market-Data-Pipline/egx_dw/.env | grep -v "^#" | xargs)'

def check_streaming_data():
    """Check if streaming data is flowing properly before running dbt"""
    import snowflake.connector
    
    conn = snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse='COMPUTE_WH'
    )
    cursor = conn.cursor()
    
    # Check if we have recent streaming data (last 6 hours)
    cursor.execute("""
        SELECT COUNT(*) 
        FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_STOCK_PRICE
        WHERE DATA_SOURCE = 'STREAMING_API'
        AND CREATED_AT > DATEADD(hour, -6, CURRENT_TIMESTAMP())
    """)
    
    recent_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    if recent_count == 0:
        raise ValueError(f"No streaming data in last 6 hours. Check producer/consumer status.")
    
    print(f"✓ Found {recent_count} streaming records in last 6 hours")
    return recent_count

# Task 1: Check streaming data health
check_data = PythonOperator(
    task_id='check_streaming_data',
    python_callable=check_streaming_data,
    dag=dag,
)

# Task 2: Run dbt deps to ensure packages are installed
dbt_deps = BashOperator(
    task_id='dbt_deps',
    bash_command=f'{DBT_VENV_ACTIVATE} && {DBT_ENV_EXPORT} && cd {DBT_PROJECT_DIR} && dbt deps',
    dag=dag,
)

# Task 3: Run staging models (Silver layer)
run_dbt_staging = BashOperator(
    task_id='run_dbt_staging',
    bash_command=f'{DBT_VENV_ACTIVATE} && {DBT_ENV_EXPORT} && cd {DBT_PROJECT_DIR} && dbt run --select staging',
    dag=dag,
)

# Task 4: Run marts models (Gold layer)
run_dbt_marts = BashOperator(
    task_id='run_dbt_marts',
    bash_command=f'{DBT_VENV_ACTIVATE} && {DBT_ENV_EXPORT} && cd {DBT_PROJECT_DIR} && dbt run --select marts',
    dag=dag,
)

# Task 5: Run dbt tests
run_dbt_tests = BashOperator(
    task_id='run_dbt_tests',
    bash_command=f'{DBT_VENV_ACTIVATE} && {DBT_ENV_EXPORT} && cd {DBT_PROJECT_DIR} && dbt test',
    dag=dag,
)

# Task 6: Generate dbt documentation
generate_dbt_docs = BashOperator(
    task_id='generate_dbt_docs',
    bash_command=f'{DBT_VENV_ACTIVATE} && {DBT_ENV_EXPORT} && cd {DBT_PROJECT_DIR} && dbt docs generate',
    dag=dag,
)

# Define task dependencies
check_data >> dbt_deps >> run_dbt_staging >> run_dbt_marts >> run_dbt_tests >> generate_dbt_docs
