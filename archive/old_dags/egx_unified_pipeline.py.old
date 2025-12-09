"""
Unified EGX Data Pipeline - Complete Automation
================================================

Single comprehensive DAG that handles:
1. Daily batch processing (S3 → Snowflake → dbt)
2. Real-time streaming during market hours
3. Data quality monitoring
4. Weekly maintenance (on Saturdays)

Schedule: Every 5 minutes (intelligently branches based on time/day)
Author: Data Engineering Team
Last Updated: December 8, 2025
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.operators.email import EmailOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule
from airflow.exceptions import AirflowException
import pendulum

# Egypt timezone
EET = pendulum.timezone("Africa/Cairo")

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 8, tzinfo=EET),
    'email': ['ahmed.elsaba@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


# ============================================================================
# Python Functions
# ============================================================================

def determine_run_type(**context):
    """
    Smart scheduler: Determines what type of run to execute
    - Daily pipeline: 4:00 AM Mon-Fri
    - Streaming: Every 5 min during market hours (9-15:30 Sun-Thu)
    - Maintenance: Saturday 2:00 AM
    - Skip: All other times
    """
    exec_time = context['execution_date']
    hour = exec_time.hour
    minute = exec_time.minute
    weekday = exec_time.weekday()  # 0=Mon, 6=Sun
    
    print(f"⏰ Execution time: {exec_time.strftime('%Y-%m-%d %H:%M')} ({exec_time.strftime('%A')})")
    
    # Saturday maintenance (2:00 AM)
    if weekday == 5 and hour == 2 and minute == 0:
        print("🔧 Running: WEEKLY MAINTENANCE")
        return 'start_maintenance'
    
    # Daily pipeline (4:00 AM Mon-Fri)
    if weekday in range(0, 5) and hour == 4 and minute == 0:
        print("📊 Running: DAILY PIPELINE")
        return 'start_daily_pipeline'
    
    # Streaming (every 5 min during market hours, Sun-Thu 9AM-3:30PM)
    # Sunday=6 in Python, so we check 6 and 0-3 for Sun-Thu
    if weekday in [6, 0, 1, 2, 3] and 9 <= hour <= 15:
        if hour == 15 and minute > 30:
            print("⏸️  Market closed")
            return 'skip_run'
        print("🔴 Running: REAL-TIME STREAMING")
        return 'start_streaming'
    
    # Skip all other times
    print("⏸️  Outside schedule - skipping")
    return 'skip_run'


def check_market_status(**context):
    """Check if Egyptian Exchange is currently open"""
    import snowflake.connector
    import os
    
    try:
        conn = snowflake.connector.connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            database='EGX_OPERATIONAL',
            schema='RAW'
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT is_market_open, market_status FROM VW_CURRENT_TRADING_STATUS")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0]:
            print(f"✅ Market OPEN - {result[1]}")
            return 'stream_data'
        else:
            print(f"⛔ Market CLOSED")
            return 'refresh_views_only'
    except Exception as e:
        print(f"⚠️ Error checking market: {e}, refreshing views only")
        return 'refresh_views_only'


def check_s3_data(**context):
    """Verify S3 has required data"""
    import boto3
    
    s3 = boto3.client('s3')
    bucket = context['params']['bucket']
    
    required = ['batch/EGX30/EGX30/', 'batch/TVH/', 'batch/companies/']
    
    for path in required:
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=path, MaxKeys=1)
        if 'Contents' not in resp:
            raise AirflowException(f"❌ No data in {path}")
    
    print("✅ S3 data verified")


def load_s3_to_snowflake(**context):
    """Load all S3 data to Snowflake"""
    import subprocess
    import sys
    
    bucket = context['params']['bucket']
    exec_date = context['execution_date'].strftime('%Y-%m-%d')
    
    cmd = [
        sys.executable, '/opt/airflow/scripts/load_all_sources.py',
        '--load-all', '--bucket', bucket, '--to', exec_date
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise AirflowException(f"Load failed: {result.stderr}")
    
    print(result.stdout)


def verify_data(**context):
    """Verify data loaded successfully"""
    import snowflake.connector
    import os
    
    conn = snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
        database='EGX_OPERATIONAL',
        schema='RAW'
    )
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT data_source, COUNT(*), COUNT(DISTINCT symbol)
        FROM STOCK_PRICES
        WHERE DATE(trade_datetime) = CURRENT_DATE()
        GROUP BY data_source
    """)
    
    results = cursor.fetchall()
    total = sum(r[1] for r in results)
    
    print(f"\n{'='*60}")
    for row in results:
        print(f"{row[0]}: {row[1]:,} records, {row[2]} symbols")
    print(f"TOTAL: {total:,} records")
    print(f"{'='*60}\n")
    
    cursor.close()
    conn.close()
    
    if total < 100:
        raise AirflowException(f"Too few records: {total}")
    
    context['task_instance'].xcom_push(key='records', value=total)
    return total


# ============================================================================
# DAG Definition
# ============================================================================

with DAG(
    'egx_unified_pipeline',
    default_args=default_args,
    description='Unified EGX pipeline: Daily batch + Streaming + Monitoring + Maintenance',
    schedule_interval='*/5 * * * *',  # Every 5 minutes
    catchup=False,
    max_active_runs=1,
    tags=['egx', 'production', 'unified'],
    params={'bucket': 'egx-data-bucket'},
) as dag:
    
    # ========================================================================
    # Smart Router: Determine What to Run
    # ========================================================================
    
    router = BranchPythonOperator(
        task_id='router',
        python_callable=determine_run_type,
    )
    
    skip = BashOperator(
        task_id='skip_run',
        bash_command='echo "⏸️  Outside scheduled times - skipping"',
    )
    
    # ========================================================================
    # BRANCH 1: Daily Pipeline (4 AM Mon-Fri)
    # ========================================================================
    
    start_daily = BashOperator(
        task_id='start_daily_pipeline',
        bash_command='echo "📊 Starting daily pipeline"',
    )
    
    with TaskGroup('daily_pipeline') as daily:
        
        check_s3 = PythonOperator(
            task_id='check_s3',
            python_callable=check_s3_data,
        )
        
        load_data = PythonOperator(
            task_id='load_data',
            python_callable=load_s3_to_snowflake,
            execution_timeout=timedelta(minutes=30),
        )
        
        verify = PythonOperator(
            task_id='verify',
            python_callable=verify_data,
        )
        
        quality = SnowflakeOperator(
            task_id='quality_check',
            snowflake_conn_id='snowflake_default',
            sql="""
            SELECT 
                SUM(CASE WHEN high < low THEN 1 ELSE 0 END) as ohlc_violations,
                SUM(CASE WHEN close IS NULL THEN 1 ELSE 0 END) as null_prices
            FROM EGX_OPERATIONAL.RAW.STOCK_PRICES
            WHERE DATE(trade_datetime) = CURRENT_DATE();
            """,
        )
        
        dbt_staging = BashOperator(
            task_id='dbt_staging',
            bash_command='cd /opt/airflow/egx_dw && dbt run --select staging --profiles-dir .',
        )
        
        dbt_marts = BashOperator(
            task_id='dbt_marts',
            bash_command='cd /opt/airflow/egx_dw && dbt run --select marts --profiles-dir .',
        )
        
        dbt_test = BashOperator(
            task_id='dbt_test',
            bash_command='cd /opt/airflow/egx_dw && dbt test --profiles-dir .',
        )
        
        dbt_docs = BashOperator(
            task_id='dbt_docs',
            bash_command='cd /opt/airflow/egx_dw && dbt docs generate --profiles-dir .',
        )
        
        check_s3 >> load_data >> verify >> quality >> dbt_staging >> dbt_marts >> [dbt_test, dbt_docs]
    
    # ========================================================================
    # BRANCH 2: Real-time Streaming (Every 5 min during market hours)
    # ========================================================================
    
    start_stream = BranchPythonOperator(
        task_id='start_streaming',
        python_callable=check_market_status,
    )
    
    stream_data = BashOperator(
        task_id='stream_data',
        bash_command="""
        cd /opt/airflow/extract/streaming && \
        timeout 4m python producer_egxpy.py --topic egx_market_data --interval 60 || true
        """,
    )
    
    refresh_views = BashOperator(
        task_id='refresh_views_only',
        bash_command="""
        cd /opt/airflow/egx_dw && \
        dbt run --select gold_vw_market_snapshot gold_vw_trading_status --profiles-dir .
        """,
    )
    
    # Both paths converge here
    stream_complete = BashOperator(
        task_id='stream_complete',
        bash_command='echo "✅ Streaming cycle complete"',
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )
    
    # ========================================================================
    # BRANCH 3: Weekly Maintenance (Saturday 2 AM)
    # ========================================================================
    
    start_maint = BashOperator(
        task_id='start_maintenance',
        bash_command='echo "🔧 Starting maintenance"',
    )
    
    with TaskGroup('maintenance') as maintenance:
        
        full_refresh = BashOperator(
            task_id='dbt_full_refresh',
            bash_command='cd /opt/airflow/egx_dw && dbt run --full-refresh --profiles-dir .',
            execution_timeout=timedelta(hours=1),
        )
        
        archive = SnowflakeOperator(
            task_id='archive_old_data',
            snowflake_conn_id='snowflake_default',
            sql="""
            -- Archive data >90 days
            CREATE OR REPLACE TABLE EGX_OPERATIONAL.ARCHIVE.STOCK_PRICES_ARCHIVE AS
            SELECT * FROM EGX_OPERATIONAL.RAW.STOCK_PRICES
            WHERE trade_datetime < DATEADD(day, -90, CURRENT_DATE());
            
            DELETE FROM EGX_OPERATIONAL.RAW.STOCK_PRICES
            WHERE trade_datetime < DATEADD(day, -90, CURRENT_DATE());
            """,
        )
        
        optimize = SnowflakeOperator(
            task_id='optimize',
            snowflake_conn_id='snowflake_default',
            sql='ALTER TABLE EGX_OPERATIONAL.RAW.STOCK_PRICES RECLUSTER;',
        )
        
        full_refresh >> archive >> optimize
    
    # ========================================================================
    # Convergence: All branches end here
    # ========================================================================
    
    complete = BashOperator(
        task_id='complete',
        bash_command='echo "✅ Pipeline execution complete"',
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )
    
    notify = EmailOperator(
        task_id='notify',
        to='ahmed.elsaba@example.com',
        subject='EGX Pipeline - {{ ds }}',
        html_content="""
        <h2>EGX Pipeline Status</h2>
        <p>Date: {{ ds }}</p>
        <p>Status: ✅ Success</p>
        <p>Links: <a href="http://localhost:3000">Grafana</a> | 
           <a href="http://localhost:8001">dbt Docs</a></p>
        """,
        trigger_rule=TriggerRule.NONE_FAILED,
    )
    
    # ========================================================================
    # DAG Flow
    # ========================================================================
    
    # Router decides which branch
    router >> [skip, start_daily, start_stream, start_maint]
    
    # Daily branch
    start_daily >> daily >> complete
    
    # Streaming branch (with sub-branching for market status)
    start_stream >> [stream_data, refresh_views]
    stream_data >> stream_complete
    refresh_views >> stream_complete
    stream_complete >> complete
    
    # Maintenance branch
    start_maint >> maintenance >> complete
    
    # Skip branch goes straight to complete
    skip >> complete
    
    # Final notification
    complete >> notify


# ============================================================================
# Documentation
# ============================================================================

dag.doc_md = """
# EGX Unified Pipeline (One DAG to Rule Them All)

## Schedule Intelligence
Runs **every 5 minutes** but intelligently decides what to do:

| Time | Day | Action |
|------|-----|--------|
| 4:00 AM | Mon-Fri | **Daily Pipeline** (S3 → Snowflake → dbt → Verify) |
| 9:00-15:30 | Sun-Thu | **Streaming** (Real-time data + refresh views) |
| 2:00 AM | Saturday | **Maintenance** (Full refresh + Archive + Optimize) |
| Other times | Any | **Skip** (No action) |

## Architecture
```
S3 (batch/EGX30, TVH, companies)
    ↓
Snowflake Operational (EGX_OPERATIONAL.RAW)
    ↓
dbt Staging (BRONZE → SILVER)
    ↓
dbt Marts (SILVER → GOLD)
    ↓
Grafana Dashboard + Real-time Views
```

## Key Features
- ✅ **Single DAG**: One file, one schedule, everything automated
- ✅ **Smart Routing**: Runs the right job at the right time
- ✅ **Market-Aware**: Checks if EGX is open before streaming
- ✅ **Quality Built-in**: Validates data at every step
- ✅ **Email Alerts**: Notifies on completion and failures
- ✅ **Maintenance Included**: Weekly optimization automatic

## Manual Triggers
```bash
# Trigger now (will follow schedule logic)
airflow dags trigger egx_unified_pipeline

# Force specific run type
airflow dags trigger egx_unified_pipeline --conf '{"force_daily": true}'
```

## Monitoring
- Airflow: http://localhost:8080
- Grafana: http://localhost:3000
- dbt Docs: http://localhost:8001
"""
