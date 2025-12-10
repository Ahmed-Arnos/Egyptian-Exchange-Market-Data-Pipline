"""
EGX Stock Data Processor
Consumes stock data from Kafka and inserts into QuestDB
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional
import requests
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'egx-stock-data')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'egx-processor-group')
QUESTDB_HOST = os.getenv('QUESTDB_HOST', 'localhost')
QUESTDB_PORT = int(os.getenv('QUESTDB_PORT', '9000'))


class EGXStockProcessor:
    """Processor for EGX stock market data"""
    
    def __init__(self):
        self.consumer = self._create_consumer()
        self.questdb_url = f"http://{QUESTDB_HOST}:{QUESTDB_PORT}"
        self._ensure_table_exists()
        logger.info(f"✓ Processor initialized")
        
    def _create_consumer(self) -> KafkaConsumer:
        """Create and configure Kafka consumer with retry logic"""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                consumer = KafkaConsumer(
                    KAFKA_TOPIC,
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    group_id=KAFKA_GROUP_ID,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    max_poll_records=100
                )
                logger.info(f"✓ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
                logger.info(f"✓ Subscribed to topic: {KAFKA_TOPIC}")
                return consumer
            except KafkaError as e:
                logger.warning(f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached. Exiting.")
                    raise
    
    def _ensure_table_exists(self):
        """Create QuestDB table if it doesn't exist"""
        try:
            # Check if table exists
            check_query = "SELECT COUNT(*) FROM egx_stock_prices LIMIT 1"
            response = requests.get(f"{self.questdb_url}/exec", params={"query": check_query})
            
            if response.status_code != 200 or 'error' in response.json():
                # Table doesn't exist, create it
                create_table_query = """
                CREATE TABLE IF NOT EXISTS egx_stock_prices (
                    ticker SYMBOL,
                    company_name STRING,
                    price DOUBLE,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    volume LONG,
                    price_change DOUBLE,
                    price_change_percent DOUBLE,
                    currency SYMBOL,
                    source STRING,
                    exchange SYMBOL,
                    timestamp TIMESTAMP
                ) timestamp(timestamp) PARTITION BY DAY;
                """
                response = requests.get(f"{self.questdb_url}/exec", params={"query": create_table_query})
                if response.status_code == 200:
                    logger.info("✓ Created table: egx_stock_prices")
                else:
                    logger.error(f"Failed to create table: {response.text}")
            else:
                logger.info("✓ Table egx_stock_prices already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring table exists: {e}")
    
    def insert_to_questdb(self, record: Dict) -> bool:
        """Insert a single record into QuestDB"""
        try:
            # Extract values with defaults
            ticker = record.get('ticker', '')
            company_name = record.get('company_name', '')
            price = record.get('price', 0.0)
            open_price = record.get('open', 0.0)
            high = record.get('high', 0.0)
            low = record.get('low', 0.0)
            volume = record.get('volume', 0)
            price_change = record.get('price_change', 0.0)
            price_change_percent = record.get('price_change_percent', 0.0)
            currency = record.get('currency', 'EGP')
            source = record.get('source', '')
            exchange = record.get('exchange', 'EGX')
            timestamp = record.get('timestamp', datetime.utcnow().isoformat())
            
            # Convert ISO timestamp to QuestDB format
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            ts_micro = int(ts.timestamp() * 1_000_000)
            
            # Insert query
            insert_query = f"""
            INSERT INTO egx_stock_prices VALUES(
                '{ticker}',
                '{company_name.replace("'", "''")}',
                {price},
                {open_price},
                {high},
                {low},
                {volume},
                {price_change},
                {price_change_percent},
                '{currency}',
                '{source}',
                '{exchange}',
                {ts_micro}
            );
            """
            
            response = requests.get(f"{self.questdb_url}/exec", params={"query": insert_query})
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Failed to insert {ticker}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error inserting record for {record.get('ticker', 'UNKNOWN')}: {e}")
            return False
    
    def run(self):
        """Main processor loop"""
        logger.info("🚀 Starting EGX Stock Data Processor")
        logger.info(f"   Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"   Topic: {KAFKA_TOPIC}")
        logger.info(f"   QuestDB: {self.questdb_url}")
        
        processed_count = 0
        error_count = 0
        
        try:
            for message in self.consumer:
                try:
                    record = message.value
                    
                    # Insert into QuestDB
                    if self.insert_to_questdb(record):
                        processed_count += 1
                        if processed_count % 100 == 0:
                            logger.info(f"✓ Processed {processed_count} records (errors: {error_count})")
                    else:
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Processor stopped by user")
        except Exception as e:
            logger.error(f"Processor error: {e}")
        finally:
            self.consumer.close()
            logger.info(f"Processor closed. Total processed: {processed_count}, Errors: {error_count}")


if __name__ == "__main__":
    processor = EGXStockProcessor()
    processor.run()
