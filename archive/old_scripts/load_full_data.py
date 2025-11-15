#!/usr/bin/env python3
"""
Load full S&P 500 stock data into database
This script fetches historical prices and fundamentals for all S&P 500 stocks
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from datetime import datetime
import pandas as pd
from config import Config
from data.storage import DatabaseManager
from data.collectors import StockDataCollector
from data.pipeline import get_sp500_tickers

def load_stock_data(db_manager, collector, ticker, delay=0.5):
    """
    Load data for a single stock
    
    Args:
        db_manager: DatabaseManager instance
        collector: StockDataCollector instance
        ticker: Stock ticker symbol
        delay: Delay in seconds between requests (for rate limiting)
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        print(f"  Fetching data for {ticker}...", end=" ")
        
        # Fetch company info
        info = collector.fetch_company_info(ticker)
        
        # Add stock to database
        stock = db_manager.add_stock(
            ticker=ticker,
            company_name=info.get('company_name', ticker),
            sector=info.get('sector', 'Unknown'),
            industry=info.get('industry', 'Unknown'),
            market_cap=info.get('market_cap')
        )
        
        # Fetch historical prices (1 year)
        df = collector.fetch_price_history(ticker, period='1y')
        
        if df is not None and not df.empty:
            # Add prices to database
            db_manager.bulk_insert_prices(stock.id, df)
            print(f"✓ {len(df)} days of price data")
        else:
            print(f"⚠ No price data")
            return False, "No price data"
        
        # Fetch fundamentals
        try:
            fundamentals = collector.fetch_fundamentals(ticker)
            
            if fundamentals:
                db_manager.add_fundamental(
                    stock_id=stock.id,
                    pe_ratio=fundamentals.get('pe_ratio'),
                    pb_ratio=fundamentals.get('pb_ratio'),
                    ps_ratio=fundamentals.get('ps_ratio'),
                    debt_to_equity=fundamentals.get('debt_to_equity'),
                    current_ratio=fundamentals.get('current_ratio'),
                    quick_ratio=fundamentals.get('quick_ratio'),
                    roe=fundamentals.get('roe'),
                    roa=fundamentals.get('roa'),
                    profit_margin=fundamentals.get('profit_margin'),
                    revenue_growth=fundamentals.get('revenue_growth'),
                    earnings_growth=fundamentals.get('earnings_growth')
                )
        except Exception as e:
            print(f"    (fundamentals failed: {str(e)[:50]})")
        
        # Rate limiting delay
        time.sleep(delay)
        
        return True, "Success"
        
    except Exception as e:
        print(f"✗ Error: {str(e)[:50]}")
        return False, str(e)


def main():
    """Main data loading function"""
    print("=" * 80)
    print("SmartInvest Bot - Full Data Loader")
    print("=" * 80)
    print()
    
    # Initialize components
    print("🔧 Initializing...")
    config = Config()
    db_manager = DatabaseManager(config.DATABASE_URL)
    collector = StockDataCollector()
    
    # Get S&P 500 tickers
    print("\n📊 Fetching S&P 500 ticker list...")
    tickers = get_sp500_tickers()
    print(f"   Found {len(tickers)} tickers")
    
    # Filter valid tickers
    print("\n🔍 Filtering tickers...")
    valid_tickers = collector.filter_universe(tickers, min_price=5, min_volume=500000)
    print(f"   {len(valid_tickers)} tickers pass filters")
    
    # Ask for confirmation
    print(f"\n⚠️  About to load {len(valid_tickers)} stocks")
    print(f"   Estimated time: {len(valid_tickers) * 0.5 / 60:.0f} minutes")
    response = input("\n   Continue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("   Cancelled.")
        return
    
    # Load data
    print(f"\n📥 Loading data for {len(valid_tickers)} stocks...")
    print("   (This will take a while - grab a coffee! ☕)\n")
    
    start_time = datetime.now()
    successful = []
    failed = []
    
    for i, ticker in enumerate(valid_tickers, 1):
        print(f"[{i}/{len(valid_tickers)}] {ticker}", end=" ")
        
        success, message = load_stock_data(db_manager, collector, ticker)
        
        if success:
            successful.append(ticker)
        else:
            failed.append((ticker, message))
        
        # Progress update every 50 stocks
        if i % 50 == 0:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            remaining = (len(valid_tickers) - i) * (elapsed / i)
            print(f"\n   Progress: {i}/{len(valid_tickers)} ({i/len(valid_tickers)*100:.1f}%)")
            print(f"   Elapsed: {elapsed:.1f} min | Remaining: ~{remaining:.1f} min\n")
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds() / 60
    
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"✅ Successful: {len(successful)} stocks")
    print(f"❌ Failed: {len(failed)} stocks")
    print(f"⏱️  Time: {elapsed:.1f} minutes")
    print(f"📊 Success rate: {len(successful)/len(valid_tickers)*100:.1f}%")
    
    if failed:
        print("\n❌ Failed tickers:")
        for ticker, msg in failed[:10]:  # Show first 10
            print(f"   {ticker}: {msg[:50]}")
        if len(failed) > 10:
            print(f"   ... and {len(failed) - 10} more")
    
    print("\n✅ Data loading complete!")
    print("\nNext steps:")
    print("   1. Run: python scripts/fetch_news_sentiment.py")
    print("   2. Then: python scripts/train_model.py")
    print("=" * 80)


if __name__ == "__main__":
    main()

