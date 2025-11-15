"""
Refresh fundamentals ONLY using yfinance.
Quick script to update fundamental metrics without touching prices or news.
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime
import yfinance as yf

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from data.storage import DatabaseManager
from data.schema import Fundamental

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def refresh_fundamentals_only(db_manager, batch_size=50):
    """
    Refresh fundamental data using yfinance (free, no API limits).
    Updates quarterly metrics like P/E, ROE, debt ratios, etc.
    
    Args:
        db_manager: DatabaseManager instance
        batch_size: Number of stocks per batch
    """
    logger.info("\n📈 Refreshing fundamentals using yfinance (FREE)...")
    
    stocks = db_manager.get_all_stocks()
    total = len(stocks)
    success_count = 0
    fail_count = 0
    
    logger.info(f"Found {total} stocks to process\n")
    
    for i in range(0, total, batch_size):
        batch = stocks[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total // batch_size) + 1
        
        logger.info(f"\n📦 Batch {batch_num}/{total_batches}")
        
        for stock in batch:
            try:
                logger.info(f"  [{stock.ticker}] Fetching fundamentals...")
                
                # Fetch fundamentals using yfinance
                yf_stock = yf.Ticker(stock.ticker)
                info = yf_stock.info
                
                # Extract key metrics
                fundamentals = {
                    'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                    'pb_ratio': info.get('priceToBook'),
                    'roe': info.get('returnOnEquity'),  # Decimal (e.g., 0.15 = 15%)
                    'roa': info.get('returnOnAssets'),
                    'debt_to_equity': info.get('debtToEquity'),
                    'current_ratio': info.get('currentRatio'),
                    'profit_margin': info.get('profitMargins'),
                    'revenue_growth': info.get('revenueGrowth'),
                    'earnings_growth': info.get('earningsGrowth'),
                    'free_cash_flow': info.get('freeCashflow'),
                }
                
                # Count available metrics
                available_metrics = sum(1 for v in fundamentals.values() if v is not None)
                
                if available_metrics > 0:
                    # Store in database
                    fundamental_record = Fundamental(
                        stock_id=stock.id,
                        date=datetime.now(),
                        pe_ratio=fundamentals.get('pe_ratio'),
                        pb_ratio=fundamentals.get('pb_ratio'),
                        roe=fundamentals.get('roe'),
                        roa=fundamentals.get('roa'),
                        debt_to_equity=fundamentals.get('debt_to_equity'),
                        current_ratio=fundamentals.get('current_ratio'),
                        profit_margin=fundamentals.get('profit_margin'),
                        revenue_growth=fundamentals.get('revenue_growth')
                    )
                    
                    # Add to database
                    session = db_manager.Session()
                    try:
                        session.add(fundamental_record)
                        session.commit()
                        logger.info(f"    ✅ Stored {available_metrics}/9 metrics")
                        success_count += 1
                    except Exception as e:
                        session.rollback()
                        logger.error(f"    ❌ Database error: {e}")
                        fail_count += 1
                    finally:
                        session.close()
                else:
                    logger.warning(f"    ⚠️  No fundamental data available")
                    fail_count += 1
                
                time.sleep(0.5)  # Rate limiting for yfinance
                
            except Exception as e:
                logger.error(f"    ❌ Error: {e}")
                fail_count += 1
                continue
        
        logger.info(f"Progress: {min(i+batch_size, total)}/{total} ({min(i+batch_size, total)/total*100:.1f}%)")
    
    logger.info(f"\n✅ Fundamentals refresh complete: {success_count} success, {fail_count} failed")
    return success_count, fail_count


def main():
    """Main execution - fundamentals only."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║        FUNDAMENTALS REFRESH ONLY - SmartInvest Bot         ║
    ╚════════════════════════════════════════════════════════════╝
    
    This script will ONLY refresh fundamentals:
    • P/E Ratio (valuation)
    • ROE (profitability)
    • Debt/Equity (financial health)
    • Profit Margins
    • Revenue & Earnings Growth
    
    Data source: yfinance (100% FREE)
    
    ⏱️  Estimated time: 4-5 minutes for 500 stocks
    
    Note: This does NOT refresh prices or news!
    
    """)
    
    start_time = datetime.now()
    logger.info(f"🚀 Starting fundamentals refresh at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize
    logger.info("Initializing database...")
    db_manager = DatabaseManager(Config.DATABASE_URL)
    
    # Stats
    total_stocks = len(db_manager.get_all_stocks())
    logger.info(f"📊 Database contains {total_stocks} stocks")
    
    if total_stocks == 0:
        logger.error("❌ No stocks in database! Run load_sp500.py first")
        return
    
    # Refresh fundamentals
    logger.info("\n" + "="*60)
    logger.info("REFRESHING FUNDAMENTALS (yfinance)")
    logger.info("="*60)
    fund_success, fund_fail = refresh_fundamentals_only(db_manager)
    
    # Final summary
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║                 FUNDAMENTALS REFRESH COMPLETE!             ║
    ╚════════════════════════════════════════════════════════════╝
    
    📊 Results:
       Fundamentals: {fund_success} ✅  {fund_fail} ❌
    
    ⏱️  Time: {elapsed/60:.1f} minutes
    🎯 Database: {total_stocks} stocks with updated fundamentals
    
    Next steps:
    1. Test dip scanner: python scripts/test_dip_scanner.py
    2. Try Discord: /dip (will use fresh fundamentals)
    
    """)
    
    logger.info(f"✅ Fundamentals refresh completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

