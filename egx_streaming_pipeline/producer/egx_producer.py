"""
Egyptian Exchange (EGX) Stock Market Data Producer
Scrapes real-time data from TradingView and publishes to Kafka
"""
import json
import logging
import os
import random
import time
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from kafka import KafkaProducer
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
FETCH_INTERVAL = int(os.getenv('FETCH_INTERVAL', '30'))  # seconds

# Top EGX stocks (from TradingView's Egypt page)
EGX_STOCKS = {
    "COMI": "Commercial International Bank (Egypt)",
    "EKHO": "El Kahera Housing",
    "HRHO": "Heliopolis Housing",
    "BTFH": "Beltone Financial Holding",
    "PHDC": "Palm Hills Developments",
    "OCDI": "Orascom Construction Industries",
    "JUFO": "Juhayna Food Industries",
    "ETEL": "Egyptian Company for Mobile Services",
    "ESRS": "Eastern Company S.A.E.",
    "SWDY": "El Swedy Electric",
    "GTHE": "GB Auto",
    "TMGH": "TMG Holding",
    "ORTE": "Oriental Weavers",
    "ALCN": "Alexandria Container and Cargo Handling",
    "HELI": "Heliopolis Company for Housing and Development",
    "SVCE": "South Valley Cement",
    "MEPA": "Medical Packaging Company",
    "NCCW": "Nasr Co. for Civil Works",
    "ICID": "International Company for Investment & Development",
    "IFAP": "International Agricultural Products",
    "BONY": "Bonyan for Development and Trade",
    "NIPH": "El Nasr Company for Intermediate Chemicals",
    "TPCO": "Tenth of Ramadan Pharmaceutical",
    "CCAP": "Credit Agricole Egypt",
    "FWRY": "Fawry for Banking Technology and Electronic Payments"
}


class EGXStockProducer:
    """Producer for Egyptian Exchange stock market data"""
    
    def __init__(self):
        self.producer = self._create_producer()
        self.tickers = list(EGX_STOCKS.keys())
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        logger.info(f"📊 Tracking {len(self.tickers)} EGX stocks")
        logger.info(f"📈 Stocks: {', '.join(self.tickers[:5])}...")
        
    def _create_producer(self) -> KafkaProducer:
        """Create and configure Kafka producer with retry logic"""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                producer = KafkaProducer(
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    acks='all',
                    retries=3,
                    max_in_flight_requests_per_connection=1,
                    compression_type='gzip'
                )
                logger.info(f"✓ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
                return producer
            except KafkaError as e:
                logger.warning(f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached. Exiting.")
                    raise
    
    def fetch_stock_data(self, ticker: str) -> Optional[Dict]:
        """
        Fetch stock data for a single ticker
        Note: TradingView requires JavaScript, so we simulate realistic data
        In production, you would use:
        - Official EGX API (if available)
        - Selenium/Playwright for JS rendering
        - Third-party financial data APIs
        """
        try:
            # Simulate realistic EGX stock data
            # In production, replace with actual scraping/API call
            base_price = random.uniform(5.0, 200.0)  # EGP
            previous_close = base_price
            
            # Realistic daily movement (-5% to +5%)
            change_percent = random.uniform(-5.0, 5.0)
            change_amount = previous_close * (change_percent / 100)
            current_price = previous_close + change_amount
            
            # Volume in thousands
            volume = random.randint(100000, 5000000)
            
            # High/Low of the day
            high = current_price + abs(random.uniform(0, change_amount))
            low = current_price - abs(random.uniform(0, change_amount))
            
            record = {
                "ticker": ticker,
                "company_name": EGX_STOCKS[ticker],
                "price": round(current_price, 2),
                "open": round(previous_close, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "volume": volume,
                "price_change": round(change_amount, 2),
                "price_change_percent": round(change_percent, 2),
                "currency": "EGP",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "tradingview_simulation",
                "exchange": "EGX"
            }
            
            return record
            
        except Exception as e:
            logger.warning(f"Error fetching data for {ticker}: {e}")
            return None
    
    def fetch_market_data(self) -> List[Dict]:
        """Fetch market data for all tracked stocks"""
        market_data = []
        
        for ticker in self.tickers:
            record = self.fetch_stock_data(ticker)
            if record:
                market_data.append(record)
            
            # Small delay to avoid overwhelming any real API
            time.sleep(0.1)
        
        return market_data
    
    def publish_data(self, market_data: List[Dict]):
        """Publish market data to Kafka"""
        if not market_data:
            logger.warning("No market data to publish")
            return
            
        for record in market_data:
            try:
                future = self.producer.send(
                    KAFKA_TOPIC,
                    key=record['ticker'],
                    value=record
                )
                future.get(timeout=10)
                
            except KafkaError as e:
                logger.error(f"Failed to send record for {record['ticker']}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending record: {e}")
        
        logger.info(f"✓ Published {len(market_data)} stock records to '{KAFKA_TOPIC}'")
    
    def run(self):
        """Main producer loop"""
        logger.info("🚀 Starting EGX Stock Market Data Producer")
        logger.info(f"   Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"   Topic: {KAFKA_TOPIC}")
        logger.info(f"   Interval: {FETCH_INTERVAL}s")
        logger.info(f"   Tracking {len(self.tickers)} stocks")
        
        try:
            iteration = 0
            while True:
                start_time = time.time()
                
                # Fetch and publish stock data
                market_data = self.fetch_market_data()
                if market_data:
                    self.publish_data(market_data)
                    logger.info(f"✓ Iteration {iteration + 1}: Published {len(market_data)} stocks")
                else:
                    logger.warning(f"⚠ Iteration {iteration + 1}: No market data fetched")
                
                iteration += 1
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, FETCH_INTERVAL - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("Producer stopped by user")
        except Exception as e:
            logger.error(f"Producer error: {e}")
        finally:
            self.producer.close()
            logger.info("Producer closed")


if __name__ == "__main__":
    producer = EGXStockProducer()
    producer.run()
