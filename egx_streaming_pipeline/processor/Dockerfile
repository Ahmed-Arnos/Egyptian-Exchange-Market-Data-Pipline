FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --default-timeout=100 --retries=5 --no-cache-dir -r requirements.txt

COPY egx_processor.py .

CMD ["python", "egx_processor.py"]
