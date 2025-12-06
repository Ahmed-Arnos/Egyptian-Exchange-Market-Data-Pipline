"""
EGX Streaming Pipeline DAG

Continuously runs producer and consumers for real-time market data streaming.
Fetches data for 16 EGX companies and streams through Kafka to InfluxDB and S3.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor
from datetime import datetime, timedelta
import os

# Get project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 16 companies to track
SYMBOLS = "COMI,ETEL,SWDY,PHDC,ORAS,ESRS,HRHO,OCDI,SKPC,TMGH,JUFO,EKHO,CLHO,OTMT,BTFH,HELI"

default_args = {
    'owner': 'egx-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 6),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'egx_streaming_pipeline',
    default_args=default_args,
    description='EGX real-time streaming: Producer + Consumers',
    schedule_interval=None,  # Manually triggered, runs continuously
    catchup=False,
    max_active_runs=1,
    tags=['egx', 'streaming', 'real-time'],
) as dag:

    # Activate virtual environment prefix
    venv_activate = f"source {PROJECT_ROOT}/.venv/bin/activate && cd {PROJECT_ROOT} && "

    # Task 1: Start Kafka Producer (EGX API → Kafka)
    # Polls every 5 minutes for new data
    start_producer = BashOperator(
        task_id='kafka_producer',
        bash_command=(
            f"{venv_activate}"
            f"python extract/egxpy_streaming/producer_kafka.py "
            f"--symbols {SYMBOLS} "
            f"--interval Daily "
            f"--n-bars 30 "
            f"--poll-interval 300 "
            f"--topic egx_market_data "
            f"--bootstrap localhost:9093"
        ),
        execution_timeout=None,  # Long-running task
    )

    # Task 2: Start InfluxDB Consumer (Kafka → InfluxDB → Grafana)
    start_consumer_influxdb = BashOperator(
        task_id='consumer_influxdb',
        bash_command=(
            f"{venv_activate}"
            f"python extract/realtime/consumer_influxdb.py "
            f"--topic egx_market_data "
            f"--bootstrap localhost:9093"
        ),
        execution_timeout=None,  # Long-running task
    )

    # Task 3: Start S3 Consumer (Kafka → S3 → Snowflake)
    start_consumer_s3 = BashOperator(
        task_id='consumer_s3',
        bash_command=(
            f"{venv_activate}"
            f"python extract/streaming/consumer_kafka.py "
            f"--topic egx_market_data "
            f"--bootstrap localhost:9093 "
            f"--bucket egx-data-bucket"
        ),
        execution_timeout=None,  # Long-running task
    )

    # Pipeline flow: Producer must start first, then consumers in parallel
    start_producer >> [start_consumer_influxdb, start_consumer_s3]
