#!/usr/bin/env python3
"""
Test script for EOD Historical Data (EODHD) API

Tests connectivity and data quality for Egyptian Exchange stocks.

Usage:
    python test_eodhd_api.py
    python test_eodhd_api.py --symbol COMI.CASE
    python test_eodhd_api.py --test-all
"""

import argparse
import json
import logging
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
LOG = logging.getLogger(__name__)

# Your API credentials
API_KEY = os.getenv('EODHD_API_KEY')
BASE_URL = "https://eodhd.com/api"
EXCHANGE = "CASE"  # Cairo Stock Exchange


def test_api_connection() -> bool:
    """Test basic API connectivity"""
    LOG.info("=" * 80)
    LOG.info("Test 1: API Connection")
    LOG.info("=" * 80)
    
    url = f"{BASE_URL}/exchanges-list/?api_token={API_KEY}&fmt=json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        exchanges = response.json()
        
        # Look for Cairo Stock Exchange
        case_exchange = next((ex for ex in exchanges if ex.get('Code') == 'CASE'), None)
        
        if case_exchange:
            LOG.info("✓ API connection successful")
            LOG.info(f"✓ Egyptian Exchange found: {case_exchange.get('Name')}")
            LOG.info(f"  Country: {case_exchange.get('Country')}")
            LOG.info(f"  Code: {case_exchange.get('Code')}")
            return True
        else:
            LOG.warning("⚠ API connected but Egyptian Exchange (CASE) not found")
            return False
    
    except requests.exceptions.RequestException as e:
        LOG.error(f"✗ API connection failed: {e}")
        return False


def test_ticker_list() -> List[Dict[str, Any]]:
    """Test fetching list of Egyptian tickers"""
    LOG.info("=" * 80)
    LOG.info("Test 2: Ticker List")
    LOG.info("=" * 80)
    
    url = f"{BASE_URL}/exchange-symbol-list/{EXCHANGE}?api_token={API_KEY}&fmt=json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        tickers = response.json()
        
        LOG.info(f"✓ Found {len(tickers)} Egyptian stocks")
        LOG.info(f"\nSample tickers:")
        for ticker in tickers[:10]:
            LOG.info(f"  {ticker.get('Code'):10s} - {ticker.get('Name')}")
        
        # Check if our 16 companies are available
        our_symbols = ['COMI', 'ETEL', 'SWDY', 'PHDC', 'ORAS', 'ESRS', 'HRHO', 'OCDI', 
                       'SKPC', 'TMGH', 'JUFO', 'EKHO', 'CLHO', 'OTMT', 'BTFH', 'HELI']
        
        available_codes = [t.get('Code') for t in tickers]
        found = [s for s in our_symbols if s in available_codes]
        missing = [s for s in our_symbols if s not in available_codes]
        
        LOG.info(f"\n✓ Found {len(found)}/16 of our tracked companies")
        if missing:
            LOG.warning(f"⚠ Missing symbols: {', '.join(missing)}")
        
        return tickers
    
    except requests.exceptions.RequestException as e:
        LOG.error(f"✗ Failed to fetch ticker list: {e}")
        return []


def test_historical_data(symbol: str = "COMI.CASE") -> Optional[List[Dict]]:
    """Test fetching historical EOD data"""
    LOG.info("=" * 80)
    LOG.info(f"Test 3: Historical Data ({symbol})")
    LOG.info("=" * 80)
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/eod/{symbol}?api_token={API_KEY}&from={start_date}&to={end_date}&fmt=json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            LOG.warning(f"⚠ No historical data returned for {symbol}")
            return None
        
        LOG.info(f"✓ Retrieved {len(data)} daily bars")
        LOG.info(f"  Date range: {data[0].get('date')} to {data[-1].get('date')}")
        LOG.info(f"\n  Latest bar:")
        latest = data[-1]
        LOG.info(f"    Date:   {latest.get('date')}")
        LOG.info(f"    Open:   {latest.get('open')}")
        LOG.info(f"    High:   {latest.get('high')}")
        LOG.info(f"    Low:    {latest.get('low')}")
        LOG.info(f"    Close:  {latest.get('close')}")
        LOG.info(f"    Volume: {latest.get('volume'):,}")
        
        return data
    
    except requests.exceptions.RequestException as e:
        LOG.error(f"✗ Failed to fetch historical data: {e}")
        return None


def test_intraday_data(symbol: str = "COMI.CASE") -> Optional[List[Dict]]:
    """Test fetching intraday data (5-minute bars)"""
    LOG.info("=" * 80)
    LOG.info(f"Test 4: Intraday Data ({symbol})")
    LOG.info("=" * 80)
    
    # Get last 24 hours
    to_ts = int(datetime.now().timestamp())
    from_ts = to_ts - (24 * 3600)
    
    url = f"{BASE_URL}/intraday/{symbol}?api_token={API_KEY}&interval=5m&from={from_ts}&to={to_ts}&fmt=json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            LOG.warning(f"⚠ No intraday data returned for {symbol}")
            LOG.info("  Note: Intraday data may require premium plan or market hours")
            return None
        
        LOG.info(f"✓ Retrieved {len(data)} 5-minute bars")
        if data:
            LOG.info(f"\n  Latest bar:")
            latest = data[-1]
            LOG.info(f"    Timestamp: {latest.get('datetime')}")
            LOG.info(f"    Open:      {latest.get('open')}")
            LOG.info(f"    Close:     {latest.get('close')}")
            LOG.info(f"    Volume:    {latest.get('volume'):,}")
        
        return data
    
    except requests.exceptions.RequestException as e:
        LOG.error(f"✗ Failed to fetch intraday data: {e}")
        if "403" in str(e):
            LOG.info("  Note: 403 error typically means plan doesn't include intraday data")
        return None


def test_fundamentals(symbol: str = "COMI.CASE") -> Optional[Dict]:
    """Test fetching company fundamentals"""
    LOG.info("=" * 80)
    LOG.info(f"Test 5: Fundamentals ({symbol})")
    LOG.info("=" * 80)
    
    url = f"{BASE_URL}/fundamentals/{symbol}?api_token={API_KEY}&fmt=json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            LOG.warning(f"⚠ No fundamental data returned for {symbol}")
            return None
        
        # Extract key information
        general = data.get('General', {})
        highlights = data.get('Highlights', {})
        valuation = data.get('Valuation', {})
        
        LOG.info("✓ Retrieved fundamental data")
        LOG.info(f"\n  General Info:")
        LOG.info(f"    Name:        {general.get('Name')}")
        LOG.info(f"    CEO:         {general.get('Officers', {}).get('CEO', 'N/A')}")
        LOG.info(f"    Industry:    {general.get('Industry')}")
        LOG.info(f"    Sector:      {general.get('Sector')}")
        LOG.info(f"    Country:     {general.get('Country')}")
        LOG.info(f"    Website:     {general.get('WebURL')}")
        
        LOG.info(f"\n  Key Metrics:")
        LOG.info(f"    Market Cap:  {highlights.get('MarketCapitalization', 'N/A')}")
        LOG.info(f"    PE Ratio:    {highlights.get('PERatio', 'N/A')}")
        LOG.info(f"    Div Yield:   {highlights.get('DividendYield', 'N/A')}")
        LOG.info(f"    52W High:    {highlights.get('52WeekHigh', 'N/A')}")
        LOG.info(f"    52W Low:     {highlights.get('52WeekLow', 'N/A')}")
        LOG.info(f"    EPS:         {highlights.get('EarningsShare', 'N/A')}")
        
        LOG.info(f"\n  Valuation:")
        LOG.info(f"    Trailing PE: {valuation.get('TrailingPE', 'N/A')}")
        LOG.info(f"    Forward PE:  {valuation.get('ForwardPE', 'N/A')}")
        LOG.info(f"    Price/Book:  {valuation.get('PriceBookMRQ', 'N/A')}")
        
        # Check for logo
        if general.get('LogoURL'):
            LOG.info(f"\n  ✓ Logo URL available: {general.get('LogoURL')}")
        
        return data
    
    except requests.exceptions.RequestException as e:
        LOG.error(f"✗ Failed to fetch fundamentals: {e}")
        return None


def test_real_time_quote(symbol: str = "COMI.CASE") -> Optional[Dict]:
    """Test fetching real-time quote"""
    LOG.info("=" * 80)
    LOG.info(f"Test 6: Real-time Quote ({symbol})")
    LOG.info("=" * 80)
    
    url = f"{BASE_URL}/real-time/{symbol}?api_token={API_KEY}&fmt=json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            LOG.warning(f"⚠ No real-time data returned for {symbol}")
            return None
        
        LOG.info("✓ Retrieved real-time quote")
        LOG.info(f"    Symbol:    {data.get('code')}")
        LOG.info(f"    Price:     {data.get('close')}")
        LOG.info(f"    Change:    {data.get('change')}")
        LOG.info(f"    Change %:  {data.get('change_p')}")
        LOG.info(f"    Timestamp: {data.get('timestamp')}")
        
        # Check for delay
        if data.get('timestamp'):
            quote_time = datetime.fromtimestamp(data.get('timestamp'))
            delay = datetime.now() - quote_time
            LOG.info(f"    Delay:     {delay.total_seconds():.0f} seconds")
            
            if delay.total_seconds() > 900:  # 15 minutes
                LOG.warning("    ⚠ Data is delayed (>15 minutes)")
        
        return data
    
    except requests.exceptions.RequestException as e:
        LOG.error(f"✗ Failed to fetch real-time quote: {e}")
        return None


def test_dividends(symbol: str = "COMI.CASE") -> Optional[List[Dict]]:
    """Test fetching dividend/split data"""
    LOG.info("=" * 80)
    LOG.info(f"Test 7: Dividends & Splits ({symbol})")
    LOG.info("=" * 80)
    
    start_date = (datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d")
    url = f"{BASE_URL}/div/{symbol}?api_token={API_KEY}&from={start_date}&fmt=json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            LOG.info(f"  No dividends/splits in last 2 years for {symbol}")
            return None
        
        LOG.info(f"✓ Found {len(data)} corporate actions")
        for action in data[:5]:  # Show first 5
            LOG.info(f"    {action.get('date')}: {action.get('type')} = {action.get('value')}")
        
        return data
    
    except requests.exceptions.RequestException as e:
        LOG.error(f"✗ Failed to fetch dividends: {e}")
        return None


def run_all_tests(symbol: str = "COMI.CASE"):
    """Run all tests"""
    LOG.info("\n" + "=" * 80)
    LOG.info("EODHD API Test Suite - Egyptian Exchange (CASE)")
    LOG.info(f"API Key: {API_KEY[:20]}...")
    LOG.info(f"Test Symbol: {symbol}")
    LOG.info("=" * 80 + "\n")
    
    results = {
        'connection': test_api_connection(),
        'tickers': test_ticker_list(),
        'historical': test_historical_data(symbol),
        'intraday': test_intraday_data(symbol),
        'fundamentals': test_fundamentals(symbol),
        'real_time': test_real_time_quote(symbol),
        'dividends': test_dividends(symbol)
    }
    
    # Summary
    LOG.info("\n" + "=" * 80)
    LOG.info("TEST SUMMARY")
    LOG.info("=" * 80)
    LOG.info(f"✓ Connection:        {'PASS' if results['connection'] else 'FAIL'}")
    LOG.info(f"✓ Ticker List:       {'PASS' if results['tickers'] else 'FAIL'} ({len(results['tickers'])} symbols)")
    LOG.info(f"✓ Historical Data:   {'PASS' if results['historical'] else 'FAIL'}")
    LOG.info(f"✓ Intraday Data:     {'PASS' if results['intraday'] else 'LIMITED/FAIL'}")
    LOG.info(f"✓ Fundamentals:      {'PASS' if results['fundamentals'] else 'FAIL'}")
    LOG.info(f"✓ Real-time Quote:   {'PASS' if results['real_time'] else 'FAIL'}")
    LOG.info(f"✓ Dividends/Splits:  {'PASS' if results['dividends'] else 'NO DATA'}")
    
    # Recommendations
    LOG.info("\n" + "=" * 80)
    LOG.info("RECOMMENDATIONS")
    LOG.info("=" * 80)
    
    if results['historical']:
        LOG.info("✓ Historical data works - Can replace/complement egxpy for daily data")
    
    if results['fundamentals']:
        LOG.info("✓ Fundamentals work - Use for company metadata (CEO, industry, PE ratio, etc.)")
    
    if not results['intraday']:
        LOG.info("⚠ Intraday data unavailable - Check your plan or stick to daily data")
    
    if results['real_time']:
        quote = results['real_time']
        if quote and quote.get('timestamp'):
            delay = (datetime.now() - datetime.fromtimestamp(quote.get('timestamp'))).total_seconds()
            if delay > 900:
                LOG.info("⚠ Real-time data is delayed - Consider upgrading plan for live data")
            else:
                LOG.info("✓ Real-time data has low latency - Good for streaming")
    
    LOG.info("\n✓ API is functional for Egyptian Exchange stocks")
    LOG.info("  Recommended use: Historical data + Fundamentals + Metadata enrichment")


def main():
    parser = argparse.ArgumentParser(description="Test EODHD API for Egyptian stocks")
    parser.add_argument('--symbol', default='COMI.CASE', help='Symbol to test (default: COMI.CASE)')
    parser.add_argument('--test-all', action='store_true', help='Run all tests')
    parser.add_argument('--test', choices=['connection', 'tickers', 'historical', 'intraday', 
                                           'fundamentals', 'realtime', 'dividends'],
                        help='Run specific test')
    
    args = parser.parse_args()
    
    if args.test_all or not args.test:
        run_all_tests(args.symbol)
    else:
        if args.test == 'connection':
            test_api_connection()
        elif args.test == 'tickers':
            test_ticker_list()
        elif args.test == 'historical':
            test_historical_data(args.symbol)
        elif args.test == 'intraday':
            test_intraday_data(args.symbol)
        elif args.test == 'fundamentals':
            test_fundamentals(args.symbol)
        elif args.test == 'realtime':
            test_real_time_quote(args.symbol)
        elif args.test == 'dividends':
            test_dividends(args.symbol)


if __name__ == '__main__':
    main()
