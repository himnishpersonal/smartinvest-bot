"""
Test script to verify the automation pipeline works end-to-end.
Tests loading, refreshing, and data preservation.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from data.storage import DatabaseManager
from data.collectors import StockDataCollector

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_load_single_stock(db_manager, collector):
    """Test loading a single stock."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Load Single Stock")
    logger.info("="*60)
    
    test_ticker = "AAPL"
    
    logger.info(f"Loading {test_ticker}...")
    success = collector.load_stock_data(test_ticker, db_manager)
    
    if success:
        logger.info(f"✅ {test_ticker} loaded successfully")
        
        # Verify data in database
        stock = db_manager.get_stock_by_ticker(test_ticker)
        if stock:
            logger.info(f"  Stock ID: {stock.id}")
            logger.info(f"  Company: {stock.company_name}")
            logger.info(f"  Sector: {stock.sector}")
            
            # Check price data
            prices = db_manager.get_price_history(stock.id)
            logger.info(f"  Price records: {len(prices)}")
            
            if prices:
                latest = prices[-1]
                logger.info(f"  Latest price: ${latest.close:.2f} on {latest.date}")
            
            return True
        else:
            logger.error(f"❌ Stock not found in database after load")
            return False
    else:
        logger.error(f"❌ Failed to load {test_ticker}")
        return False


def test_incremental_refresh(db_manager, collector):
    """Test that refresh only adds new data, preserves old."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Incremental Refresh (Data Preservation)")
    logger.info("="*60)
    
    test_ticker = "AAPL"
    
    # Get stock
    stock = db_manager.get_stock_by_ticker(test_ticker)
    if not stock:
        logger.error(f"❌ {test_ticker} not in database. Run test 1 first.")
        return False
    
    # Count existing price records
    prices_before = db_manager.get_price_history(stock.id)
    count_before = len(prices_before)
    logger.info(f"Price records before refresh: {count_before}")
    
    # Get date range before
    if prices_before:
        oldest_before = prices_before[0].date
        newest_before = prices_before[-1].date
        logger.info(f"Date range: {oldest_before} to {newest_before}")
    
    # Simulate refresh (re-run load)
    logger.info(f"\nRefreshing {test_ticker}...")
    collector.load_stock_data(test_ticker, db_manager)
    
    # Count after
    prices_after = db_manager.get_price_history(stock.id)
    count_after = len(prices_after)
    logger.info(f"\nPrice records after refresh: {count_after}")
    
    # Verify
    if count_after >= count_before:
        new_records = count_after - count_before
        logger.info(f"✅ Data preserved! Added {new_records} new records")
        
        # Check oldest date is still there
        if prices_after:
            oldest_after = prices_after[0].date
            newest_after = prices_after[-1].date
            logger.info(f"Date range: {oldest_after} to {newest_after}")
            
            if oldest_after == oldest_before:
                logger.info("✅ Historical data preserved!")
                return True
            else:
                logger.warning("⚠️  Oldest date changed - data may have been overwritten")
                return False
        return True
    else:
        logger.error(f"❌ Data lost! Had {count_before}, now have {count_after}")
        return False


def test_multiple_stocks(db_manager, collector):
    """Test loading multiple stocks."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Load Multiple Stocks")
    logger.info("="*60)
    
    test_tickers = ["MSFT", "GOOGL", "AMZN"]
    
    results = []
    for ticker in test_tickers:
        logger.info(f"\nLoading {ticker}...")
        success = collector.load_stock_data(ticker, db_manager)
        results.append(success)
        
        if success:
            stock = db_manager.get_stock_by_ticker(ticker)
            prices = db_manager.get_price_history(stock.id)
            logger.info(f"  ✅ {ticker}: {len(prices)} price records")
        else:
            logger.error(f"  ❌ {ticker}: Failed to load")
    
    success_count = sum(results)
    logger.info(f"\n{'='*60}")
    logger.info(f"Results: {success_count}/{len(test_tickers)} successful")
    
    return success_count == len(test_tickers)


def test_database_stats(db_manager):
    """Show database statistics."""
    logger.info("\n" + "="*60)
    logger.info("DATABASE STATISTICS")
    logger.info("="*60)
    
    stocks = db_manager.get_all_stocks()
    logger.info(f"Total stocks: {len(stocks)}")
    
    if stocks:
        total_prices = 0
        for stock in stocks:
            prices = db_manager.get_price_history(stock.id)
            total_prices += len(prices)
        
        logger.info(f"Total price records: {total_prices}")
        logger.info(f"Average records per stock: {total_prices / len(stocks):.0f}")
        
        # Show sample stocks
        logger.info(f"\nSample stocks:")
        for stock in stocks[:5]:
            prices = db_manager.get_price_history(stock.id)
            latest = db_manager.get_latest_price(stock.id)
            latest_date = latest.date if latest else "N/A"
            logger.info(f"  {stock.ticker:6s} - {len(prices):4d} records, latest: {latest_date}")
    
    # Database file size
    db_path = Path("smartinvest_dev.db")
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        logger.info(f"\nDatabase file size: {size_mb:.2f} MB")


def main():
    """Run all tests."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║           AUTOMATION PIPELINE TEST - SmartInvest           ║
    ╚════════════════════════════════════════════════════════════╝
    
    This script tests:
    1. Loading individual stocks
    2. Incremental refresh (data preservation)
    3. Batch loading multiple stocks
    4. Database statistics
    
    Test data: AAPL, MSFT, GOOGL, AMZN (4 stocks)
    
    """)
    
    # Initialize
    logger.info("Initializing test environment...")
    
    db_manager = DatabaseManager(Config.DATABASE_URL)
    db_manager.create_all_tables()
    
    collector = StockDataCollector(
        fmp_api_key=Config.FMP_API_KEY,
        finnhub_api_key=Config.FINNHUB_API_KEY
    )
    
    # Run tests
    results = {}
    
    results['load_single'] = test_load_single_stock(db_manager, collector)
    results['incremental'] = test_incremental_refresh(db_manager, collector)
    results['multiple'] = test_multiple_stocks(db_manager, collector)
    
    test_database_stats(db_manager)
    
    # Summary
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║                      TEST RESULTS                          ║
    ╚════════════════════════════════════════════════════════════╝
    
    Test 1 - Load Single Stock:       {'✅ PASS' if results['load_single'] else '❌ FAIL'}
    Test 2 - Incremental Refresh:     {'✅ PASS' if results['incremental'] else '❌ FAIL'}
    Test 3 - Load Multiple Stocks:    {'✅ PASS' if results['multiple'] else '❌ FAIL'}
    
    Overall: {'✅ ALL TESTS PASSED' if all(results.values()) else '❌ SOME TESTS FAILED'}
    
    Next steps:
    1. If all tests passed, you're ready to load S&P 500:
       python scripts/load_sp500.py
    
    2. Then set up daily automation:
       python scripts/setup_cron.py
    
    """)


if __name__ == "__main__":
    main()

