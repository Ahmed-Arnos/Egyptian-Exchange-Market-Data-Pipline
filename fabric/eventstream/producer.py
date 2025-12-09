#!/usr/bin/env python3
"""
Microsoft Fabric Event Streams Producer for Egyptian Exchange Market Data

Fetches EGX market data using egxpy and sends to Fabric Event Streams via Event Hub protocol.
Replaces Docker-based architecture with unified Fabric platform.

Architecture:
    EGX API → egxpy → Fabric Event Streams → KQL Database → Power BI

Usage:
    python producer.py --config config.json
    
    # Or with inline parameters
    python producer.py --connection-string "Endpoint=sb://..." --event-hub "egx_stream" --symbols COMI,ETEL

Environment Variables:
    FABRIC_EVENTHUB_CONNECTION_STRING: Event Streams connection string
    FABRIC_EVENTHUB_NAME: Event Streams name
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from typing import List, Dict, Any

try:
    from azure.eventhub import EventHubProducerClient, EventData
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("ERROR: azure-eventhub package not installed. Run: pip install azure-eventhub azure-identity")
    sys.exit(1)

try:
    from egxpy.download import get_OHLCV_data
except ImportError:
    print("ERROR: egxpy package not installed. Run: pip install git+https://github.com/egxlytics/egxpy.git")
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOG = logging.getLogger(__name__)


class FabricEventStreamProducer:
    """Producer for sending Egyptian Exchange market data to Microsoft Fabric Event Streams."""
    
    def __init__(self, connection_string: str = None, event_hub_name: str = None):
        """
        Initialize producer with connection string or Azure AD authentication.
        
        Args:
            connection_string: Event Hub-compatible connection string from Fabric Event Streams
            event_hub_name: Name of the event hub (event stream name)
        """
        self.event_hub_name = event_hub_name
        
        if connection_string:
            # Connection string authentication (recommended for custom apps)
            self.producer = EventHubProducerClient.from_connection_string(
                conn_str=connection_string,
                eventhub_name=event_hub_name
            )
            LOG.info(f"Initialized producer with connection string for event hub: {event_hub_name}")
        else:
            # Azure AD authentication (for managed identity/service principal)
            LOG.info("Connection string not provided, using Azure AD authentication")
            raise ValueError("Connection string is required. Get it from Fabric Event Streams Custom App source.")
    
    def fetch_market_data(self, symbols: List[str], exchange: str = "EGX", 
                         interval: str = "Daily", n_bars: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch market data from Egyptian Exchange using egxpy.
        
        Args:
            symbols: List of stock symbols (e.g., ['COMI', 'ETEL', 'SWDY'])
            exchange: Exchange name (default: 'EGX')
            interval: Time interval (default: 'Daily')
            n_bars: Number of historical bars to fetch
            
        Returns:
            List of market data events
        """
        events = []
        
        for symbol in symbols:
            try:
                LOG.info(f"Fetching {interval} data for {symbol} (last {n_bars} bars)...")
                df = get_OHLCV_data(symbol, exchange, interval, n_bars)
                
                if df.empty:
                    LOG.warning(f"No data returned for {symbol}")
                    continue
                
                LOG.info(f"Retrieved {len(df)} rows for {symbol}")
                
                # Convert DataFrame to event messages
                for idx, row in df.iterrows():
                    event = {
                        'symbol': symbol,
                        'exchange': exchange,
                        'interval': interval,
                        'timestamp': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                        'open': float(row.get('open', 0)),
                        'high': float(row.get('high', 0)),
                        'low': float(row.get('low', 0)),
                        'close': float(row.get('close', 0)),
                        'volume': int(row.get('volume', 0)),
                        'ingestion_time': datetime.utcnow().isoformat()
                    }
                    events.append(event)
                    
            except Exception as e:
                LOG.error(f"Failed to fetch data for {symbol}: {e}", exc_info=True)
        
        return events
    
    def send_events(self, events: List[Dict[str, Any]]) -> int:
        """
        Send events to Fabric Event Streams.
        
        Args:
            events: List of market data events
            
        Returns:
            Number of events successfully sent
        """
        if not events:
            LOG.warning("No events to send")
            return 0
        
        sent_count = 0
        
        try:
            # Create event batch
            event_data_batch = self.producer.create_batch()
            
            for event in events:
                event_json = json.dumps(event)
                event_data = EventData(event_json)
                
                # Add partition key based on symbol for proper partitioning
                event_data.properties = {'symbol': event['symbol']}
                
                try:
                    event_data_batch.add(event_data)
                    sent_count += 1
                except ValueError:
                    # Batch is full, send it and create new batch
                    LOG.info(f"Sending batch of {sent_count} events...")
                    self.producer.send_batch(event_data_batch)
                    event_data_batch = self.producer.create_batch()
                    event_data_batch.add(event_data)
                    sent_count += 1
            
            # Send remaining events
            if len(event_data_batch) > 0:
                LOG.info(f"Sending final batch of {len(event_data_batch)} events...")
                self.producer.send_batch(event_data_batch)
            
            LOG.info(f"Successfully sent {sent_count} events to Event Streams")
            
        except Exception as e:
            LOG.error(f"Failed to send events: {e}", exc_info=True)
            raise
        
        return sent_count
    
    def run_continuous(self, symbols: List[str], exchange: str = "EGX", 
                      interval: str = "Daily", n_bars: int = 100, 
                      poll_interval: int = 180):
        """
        Continuously fetch and send market data.
        
        Args:
            symbols: List of stock symbols
            exchange: Exchange name
            interval: Time interval
            n_bars: Number of bars to fetch
            poll_interval: Time between polls in seconds (default: 180s = 3 minutes)
        """
        LOG.info(f"Starting continuous streaming for {len(symbols)} symbols...")
        LOG.info(f"Poll interval: {poll_interval} seconds")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                LOG.info(f"=== Iteration {iteration} ===")
                
                # Fetch market data
                events = self.fetch_market_data(symbols, exchange, interval, n_bars)
                
                # Send to Event Streams
                if events:
                    sent = self.send_events(events)
                    LOG.info(f"Sent {sent} events in iteration {iteration}")
                else:
                    LOG.warning(f"No events fetched in iteration {iteration}")
                
                # Wait before next poll
                LOG.info(f"Waiting {poll_interval} seconds until next poll...")
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            LOG.info("Received interrupt signal, stopping producer...")
        except Exception as e:
            LOG.error(f"Fatal error in continuous mode: {e}", exc_info=True)
            raise
        finally:
            self.close()
    
    def close(self):
        """Close the producer connection."""
        try:
            self.producer.close()
            LOG.info("Producer closed successfully")
        except Exception as e:
            LOG.error(f"Error closing producer: {e}")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        LOG.error(f"Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        LOG.error(f"Invalid JSON in config file: {e}")
        sys.exit(1)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Stream Egyptian Exchange market data to Microsoft Fabric Event Streams"
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to JSON configuration file'
    )
    
    parser.add_argument(
        '--connection-string',
        type=str,
        help='Event Hub connection string from Fabric Event Streams'
    )
    
    parser.add_argument(
        '--event-hub',
        type=str,
        help='Event Hub name (Event Stream name)'
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        help='Comma-separated list of stock symbols (e.g., COMI,ETEL,SWDY)'
    )
    
    parser.add_argument(
        '--exchange',
        type=str,
        default='EGX',
        help='Exchange name (default: EGX)'
    )
    
    parser.add_argument(
        '--interval',
        type=str,
        default='Daily',
        help='Time interval (default: Daily)'
    )
    
    parser.add_argument(
        '--n-bars',
        type=int,
        default=100,
        help='Number of historical bars to fetch (default: 100)'
    )
    
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=180,
        help='Seconds between polls in continuous mode (default: 180)'
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (no continuous polling)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Load configuration
    if args.config:
        config = load_config(args.config)
        connection_string = config.get('connection_string')
        event_hub_name = config.get('event_hub_name')
        symbols = config.get('symbols', [])
        exchange = config.get('exchange', 'EGX')
        interval = config.get('interval', 'Daily')
        n_bars = config.get('n_bars', 100)
        poll_interval = config.get('poll_interval', 180)
    else:
        # Use command-line arguments or environment variables
        connection_string = args.connection_string or os.getenv('FABRIC_EVENTHUB_CONNECTION_STRING')
        event_hub_name = args.event_hub or os.getenv('FABRIC_EVENTHUB_NAME')
        symbols = args.symbols.split(',') if args.symbols else []
        exchange = args.exchange
        interval = args.interval
        n_bars = args.n_bars
        poll_interval = args.poll_interval
    
    # Validate required parameters
    if not connection_string:
        LOG.error("Connection string is required. Provide via --connection-string, config file, or FABRIC_EVENTHUB_CONNECTION_STRING env var")
        sys.exit(1)
    
    if not event_hub_name:
        LOG.error("Event hub name is required. Provide via --event-hub, config file, or FABRIC_EVENTHUB_NAME env var")
        sys.exit(1)
    
    if not symbols:
        LOG.error("Symbols list is required. Provide via --symbols or config file")
        sys.exit(1)
    
    # Initialize producer
    producer = FabricEventStreamProducer(
        connection_string=connection_string,
        event_hub_name=event_hub_name
    )
    
    # Run producer
    if args.once:
        # Single run
        LOG.info("Running in single-shot mode")
        events = producer.fetch_market_data(symbols, exchange, interval, n_bars)
        sent = producer.send_events(events)
        LOG.info(f"Sent {sent} events. Exiting.")
        producer.close()
    else:
        # Continuous mode
        producer.run_continuous(symbols, exchange, interval, n_bars, poll_interval)


if __name__ == '__main__':
    main()
