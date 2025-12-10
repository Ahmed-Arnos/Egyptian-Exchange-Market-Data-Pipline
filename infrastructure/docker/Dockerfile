FROM apache/airflow:2.9.0-python3.10

USER root
RUN apt-get update && \
    apt-get install -y git curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Docker CLI (Lightweight alternative to docker.io package)
RUN curl -SL https://download.docker.com/linux/static/stable/x86_64/docker-26.0.0.tgz -o docker.tgz && \
    tar xzvf docker.tgz --strip 1 -C /usr/local/bin docker/docker && \
    rm docker.tgz && \
    chmod +x /usr/local/bin/docker

# Install Docker Compose plugin
RUN mkdir -p /usr/local/lib/docker/cli-plugins && \
    curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose && \
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

USER airflow

# Copy requirements and install dependencies
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Install egxpy with all its dependencies (may upgrade airflow)
RUN pip install --no-cache-dir \
    git+https://github.com/egxlytics/egxpy.git

# Force reinstall airflow 2.9.0 with its constraints (this will also install compatible providers)
RUN pip install --force-reinstall --no-cache-dir \
    'apache-airflow[amazon,apache.kafka]==2.9.0' \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.0/constraints-3.10.txt"
