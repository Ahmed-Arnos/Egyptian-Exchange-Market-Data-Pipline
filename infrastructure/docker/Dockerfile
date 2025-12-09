FROM apache/airflow:2.9.0-python3.10

USER root
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow

# Install egxpy with all its dependencies (may upgrade airflow)
RUN pip install --no-cache-dir \
    git+https://github.com/egxlytics/egxpy.git

# Install additional packages
RUN pip install --no-cache-dir \
    kafka-python \
    boto3 \
    influxdb-client

# Force reinstall airflow 2.9.0 with its constraints (this will also install compatible providers)
RUN pip install --force-reinstall --no-cache-dir \
    'apache-airflow[amazon,apache.kafka]==2.9.0' \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.10.txt"
