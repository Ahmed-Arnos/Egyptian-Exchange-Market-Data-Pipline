"""
Egyptian Exchange Full Data Pipeline DAG
----------------------------------------
Complete end-to-end pipeline orchestration:
1. Check streaming pipeline health (Kafka producer/consumer)
2. Process batch data from S3 if available
3. Run dbt transformations (staging + marts)
4. Run data quality tests
5. Generate documentation

Schedule: Runs once daily at 1 AM Cairo time (23:00 UTC previous day)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
import os

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
    'email': ['ahmed@example.com'],
}

# Define the DAG
dag = DAG(
    'egx_full_pipeline',
    default_args=default_args,
    description='Full Egyptian Exchange data pipeline with batch, streaming, and analytics',
    schedule_interval='0 23 * * *',  # Run at 11 PM UTC (1 AM Cairo time)
    start_date=datetime(2025, 12, 9),
    catchup=False,
    tags=['egyptian-exchange', 'batch', 'streaming', 'dbt', 'full-pipeline'],
)

# Path configurations
REPO_ROOT = '/home/ahmed-elsaba/Git Repos/Egyptian-Exchange-Market-Data-Pipline'
DBT_PROJECT_DIR = f'{REPO_ROOT}/egx_dw'
VENV_ACTIVATE = f'source {REPO_ROOT}/.venv-aws/bin/activate'
ENV_EXPORT = f'export $(cat {DBT_PROJECT_DIR}/.env | grep -v "^#" | xargs)'

def check_batch_data_exists():
    """Check if there's new batch data in S3"""
    import boto3
    from datetime import datetime, timedelta
    
    s3 = boto3.client('s3')
    bucket_name = 'egx-data-bucket'
    
    # Check for files modified in last 24 hours
    yesterday = datetime.now() - timedelta(days=1)
    
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix='batch/')
        new_files = []
        
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['LastModified'].replace(tzinfo=None) > yesterday:
                    new_files.append(obj['Key'])
        
        print(f"Found {len(new_files)} new files in S3 in last 24 hours")
        return len(new_files) > 0
    except Exception as e:
        print(f"Warning: Could not check S3: {e}")
        return False

def check_streaming_health():
    """Check streaming pipeline health (producer and consumer)"""
    import subprocess
    
    # Check if producer and consumer processes are running
    result = subprocess.run(
        ['ps', 'aux'],
        capture_output=True,
        text=True
    )
    
    producer_running = 'producer_kafka.py' in result.stdout
    consumer_running = 'consumer_snowflake.py' in result.stdout
    
    if not producer_running:
        print("⚠ WARNING: Kafka producer is not running!")
    if not consumer_running:
        print("⚠ WARNING: Kafka consumer is not running!")
    
    # Check recent streaming data in Snowflake
    import snowflake.connector
    
    conn = snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse='COMPUTE_WH'
    )
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*), MAX(CREATED_AT)
        FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_STOCK_PRICE
        WHERE DATA_SOURCE = 'STREAMING_API'
        AND CREATED_AT > DATEADD(hour, -12, CURRENT_TIMESTAMP())
    """)
    
    count, latest = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if count == 0:
        raise ValueError("No streaming data in last 12 hours - pipeline may be down!")
    
    print(f"✓ Streaming pipeline healthy: {count} records, latest at {latest}")
    print(f"✓ Producer running: {producer_running}")
    print(f"✓ Consumer running: {consumer_running}")
    
    return True

def validate_data_quality():
    """Run data quality checks on operational tables"""
    import snowflake.connector
    
    conn = snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse='COMPUTE_WH'
    )
    cursor = conn.cursor()
    
    checks = []
    
    # Check 1: No duplicate records in TBL_COMPANY
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT SYMBOL, COUNT(*) as cnt
            FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_COMPANY
            GROUP BY SYMBOL
            HAVING cnt > 1
        )
    """)
    duplicates = cursor.fetchone()[0]
    checks.append(('No duplicate companies', duplicates == 0, f"{duplicates} duplicates found"))
    
    # Check 2: Price data has valid ranges
    cursor.execute("""
        SELECT COUNT(*)
        FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_STOCK_PRICE
        WHERE CLOSE_PRICE <= 0 OR VOLUME < 0
    """)
    invalid_prices = cursor.fetchone()[0]
    checks.append(('Valid price ranges', invalid_prices == 0, f"{invalid_prices} invalid prices"))
    
    # Check 3: Recent data exists
    cursor.execute("""
        SELECT COUNT(*)
        FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_STOCK_PRICE
        WHERE CREATED_AT > DATEADD(day, -2, CURRENT_TIMESTAMP())
    """)
    recent_count = cursor.fetchone()[0]
    checks.append(('Recent data exists', recent_count > 100, f"{recent_count} recent records"))
    
    cursor.close()
    conn.close()
    
    # Report results
    print("\n=== Data Quality Checks ===")
    all_passed = True
    for check_name, passed, detail in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check_name} - {detail}")
        if not passed:
            all_passed = False
    
    if not all_passed:
        raise ValueError("Data quality checks failed!")
    
    return True

# Start task
start = DummyOperator(task_id='start', dag=dag)

# Check 1: Streaming pipeline health
check_streaming = PythonOperator(
    task_id='check_streaming_health',
    python_callable=check_streaming_health,
    dag=dag,
)

# Check 2: Batch data availability
check_batch = PythonOperator(
    task_id='check_batch_data',
    python_callable=check_batch_data_exists,
    dag=dag,
)

# Process batch data if available (Python script)
process_batch = BashOperator(
    task_id='process_batch_data',
    bash_command=f'{VENV_ACTIVATE} && {ENV_EXPORT} && cd {REPO_ROOT}/extract && python batch_processor.py',
    dag=dag,
)

# Data quality validation on operational layer
validate_quality = PythonOperator(
    task_id='validate_data_quality',
    python_callable=validate_data_quality,
    dag=dag,
)

# Install dbt dependencies
dbt_deps = BashOperator(
    task_id='dbt_deps',
    bash_command=f'{VENV_ACTIVATE} && {ENV_EXPORT} && cd {DBT_PROJECT_DIR} && dbt deps',
    dag=dag,
)

# Run dbt staging models (Silver layer)
dbt_staging = BashOperator(
    task_id='dbt_run_staging',
    bash_command=f'{VENV_ACTIVATE} && {ENV_EXPORT} && cd {DBT_PROJECT_DIR} && dbt run --select staging',
    dag=dag,
)

# Run dbt marts models (Gold layer)
dbt_marts = BashOperator(
    task_id='dbt_run_marts',
    bash_command=f'{VENV_ACTIVATE} && {ENV_EXPORT} && cd {DBT_PROJECT_DIR} && dbt run --select marts',
    dag=dag,
)

# Run dbt tests
dbt_test = BashOperator(
    task_id='dbt_test',
    bash_command=f'{VENV_ACTIVATE} && {ENV_EXPORT} && cd {DBT_PROJECT_DIR} && dbt test',
    dag=dag,
)

# Generate dbt documentation
dbt_docs = BashOperator(
    task_id='dbt_docs_generate',
    bash_command=f'{VENV_ACTIVATE} && {ENV_EXPORT} && cd {DBT_PROJECT_DIR} && dbt docs generate',
    dag=dag,
)

# Cleanup old logs
cleanup = BashOperator(
    task_id='cleanup_old_logs',
    bash_command=f'find {REPO_ROOT} -name "*.log" -mtime +7 -delete || true',
    dag=dag,
)

# End task
end = DummyOperator(task_id='end', dag=dag)

# Define task dependencies
start >> [check_streaming, check_batch]
[check_streaming, check_batch] >> process_batch
process_batch >> validate_quality
validate_quality >> dbt_deps >> dbt_staging >> dbt_marts >> dbt_test >> dbt_docs
dbt_docs >> cleanup >> end
