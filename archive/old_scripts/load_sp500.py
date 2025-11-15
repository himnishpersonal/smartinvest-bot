"""
Load S&P 500 stocks into the database.
Fetches the official S&P 500 list and loads company info + historical data.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import yfinance as yf
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from data.storage import DatabaseManager
from data.collectors import StockDataCollector
from data.schema import Base

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_sp500_tickers():
    """
    Fetch S&P 500 ticker list from Wikipedia.
    
    Returns:
        List of ticker symbols
    """
    logger.info("Fetching S&P 500 ticker list from Wikipedia...")
    try:
        # Wikipedia maintains an updated S&P 500 list
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp500_table = tables[0]
        
        tickers = sp500_table['Symbol'].tolist()
        
        # Clean ticker symbols (fix special characters)
        tickers = [t.replace('.', '-') for t in tickers]  # BRK.B -> BRK-B
        
        logger.info(f"✅ Found {len(tickers)} S&P 500 stocks")
        return tickers
    
    except Exception as e:
        logger.error(f"❌ Failed to fetch S&P 500 list: {e}")
        logger.info("Using fallback ticker list...")
        
        # Fallback: Top 500 most liquid stocks
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'V', 'UNH',
            'LLY', 'JPM', 'XOM', 'JNJ', 'WMT', 'MA', 'PG', 'AVGO', 'HD', 'CVX',
            'MRK', 'ABBV', 'COST', 'KO', 'PEP', 'ADBE', 'BAC', 'CRM', 'TMO', 'NFLX',
            'MCD', 'CSCO', 'ACN', 'LIN', 'ABT', 'AMD', 'DHR', 'NKE', 'DIS', 'VZ',
            'CMCSA', 'WFC', 'PM', 'TXN', 'NEE', 'INTU', 'ORCL', 'COP', 'RTX', 'UNP',
            'IBM', 'QCOM', 'BMY', 'AMGN', 'HON', 'LOW', 'ELV', 'AMAT', 'T', 'SPGI',
            'UPS', 'BA', 'DE', 'GE', 'AXP', 'BLK', 'SBUX', 'CAT', 'PLD', 'GS',
            'BKNG', 'MDT', 'GILD', 'MMC', 'ADI', 'C', 'ISRG', 'VRTX', 'ADP', 'TJX',
            'MDLZ', 'REGN', 'LRCX', 'AMT', 'CI', 'MO', 'SYK', 'CB', 'SCHW', 'ZTS',
            'TMUS', 'EQIX', 'PGR', 'NOC', 'BDX', 'BSX', 'SO', 'EOG', 'DUK', 'ETN'
        ]


def load_stocks_incremental(tickers, db_manager, collector, batch_size=50, delay=1.0):
    """
    Load stocks incrementally with progress tracking.
    
    Args:
        tickers: List of ticker symbols
        db_manager: DatabaseManager instance
        collector: StockDataCollector instance
        batch_size: Number of stocks to load per batch
        delay: Delay between batches (seconds)
    """
    total = len(tickers)
    success_count = 0
    fail_count = 0
    
    logger.info(f"📊 Starting incremental load of {total} stocks...")
    logger.info(f"⏱️  Estimated time: {(total * 3) / 60:.1f} minutes")
    
    start_time = datetime.now()
    
    for i in range(0, total, batch_size):
        batch = tickers[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total // batch_size) + 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📦 BATCH {batch_num}/{total_batches} ({len(batch)} stocks)")
        logger.info(f"{'='*60}")
        
        for idx, ticker in enumerate(batch, 1):
            try:
                global_idx = i + idx
                logger.info(f"[{global_idx}/{total}] Processing {ticker}...")
                
                # Load stock data
                success = collector.load_stock_data(ticker, db_manager)
                
                if success:
                    success_count += 1
                    logger.info(f"  ✅ {ticker} loaded successfully")
                else:
                    fail_count += 1
                    logger.warning(f"  ⚠️  {ticker} failed to load")
                
                # Rate limiting
                time.sleep(delay)
                
            except Exception as e:
                fail_count += 1
                logger.error(f"  ❌ Error loading {ticker}: {e}")
                continue
        
        # Progress report
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = global_idx / elapsed if elapsed > 0 else 0
        remaining = (total - global_idx) / rate if rate > 0 else 0
        
        logger.info(f"\n📈 Progress: {global_idx}/{total} ({global_idx/total*100:.1f}%)")
        logger.info(f"✅ Success: {success_count} | ❌ Failed: {fail_count}")
        logger.info(f"⏱️  Elapsed: {elapsed/60:.1f}m | Remaining: ~{remaining/60:.1f}m")
        
        # Batch delay
        if i + batch_size < total:
            logger.info(f"⏸️  Batch complete. Waiting {delay}s before next batch...")
            time.sleep(delay)
    
    # Final report
    elapsed_total = (datetime.now() - start_time).total_seconds()
    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 LOAD COMPLETE!")
    logger.info(f"{'='*60}")
    logger.info(f"✅ Success: {success_count}/{total} ({success_count/total*100:.1f}%)")
    logger.info(f"❌ Failed: {fail_count}/{total} ({fail_count/total*100:.1f}%)")
    logger.info(f"⏱️  Total time: {elapsed_total/60:.1f} minutes")
    logger.info(f"{'='*60}\n")


def main():
    """Main execution."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║          S&P 500 STOCK LOADER - SmartInvest Bot            ║
    ╚════════════════════════════════════════════════════════════╝
    
    This script will:
    1. Fetch S&P 500 ticker list (Wikipedia)
    2. Load company info for each stock
    3. Download 5 years of historical price data
    4. Save everything to database
    
    API Limits:
    • FMP: 250 calls/day
    • yfinance: Unlimited (best effort)
    
    Strategy:
    • Process 500 stocks over 2 days (250/day)
    • Use yfinance for historical data (unlimited)
    • Use FMP for company info (250 calls)
    
    ⏱️  Estimated time: ~25 minutes per 250 stocks
    
    """)
    
    # Confirm
    response = input("Start loading S&P 500 stocks? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Cancelled by user")
        return
    
    # Initialize
    logger.info("Initializing database and collectors...")
    
    db_manager = DatabaseManager(Config.DATABASE_URL)
    db_manager.create_all_tables()
    
    collector = StockDataCollector(
        fmp_api_key=Config.FMP_API_KEY,
        finnhub_api_key=Config.FINNHUB_API_KEY
    )
    
    # Get S&P 500 tickers
    tickers = get_sp500_tickers()
    
    # Check how many we can load today (respect API limits)
    existing_stocks = db_manager.get_all_stocks()
    existing_tickers = {s.ticker for s in existing_stocks}
    new_tickers = [t for t in tickers if t not in existing_tickers]
    
    logger.info(f"📊 Stocks in database: {len(existing_tickers)}")
    logger.info(f"📊 New stocks to load: {len(new_tickers)}")
    
    if len(new_tickers) == 0:
        logger.info("✅ All S&P 500 stocks already loaded!")
        return
    
    # Limit to 250/day (FMP API limit)
    daily_limit = 250
    if len(new_tickers) > daily_limit:
        logger.warning(f"⚠️  Can only load {daily_limit} stocks today (API limit)")
        logger.info(f"📅 Will need {len(new_tickers) // daily_limit + 1} days to complete")
        to_load = new_tickers[:daily_limit]
    else:
        to_load = new_tickers
    
    logger.info(f"📦 Loading {len(to_load)} stocks today")
    
    # Load stocks
    load_stocks_incremental(
        tickers=to_load,
        db_manager=db_manager,
        collector=collector,
        batch_size=25,  # 25 stocks per batch
        delay=0.5  # 0.5s delay between stocks
    )
    
    # Database stats
    all_stocks = db_manager.get_all_stocks()
    logger.info(f"\n📊 Database now contains {len(all_stocks)} stocks")
    
    if len(new_tickers) > daily_limit:
        remaining = len(new_tickers) - daily_limit
        logger.info(f"\n📅 To complete S&P 500, run this script again tomorrow")
        logger.info(f"   ({remaining} stocks remaining)")


if __name__ == "__main__":
    main()

