"""
Daily data refresh script for SmartInvest bot.
Updates existing stock data with latest prices, fundamentals, and news.
Preserves all historical data for ML training.
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from data.storage import DatabaseManager
from data.collectors import StockDataCollector, NewsCollector, SentimentAnalyzer
from data.schema import Base

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def refresh_stock_prices(db_manager, collector, batch_size=50):
    """
    Refresh stock prices with latest data.
    Only adds NEW data points, preserves historical data.
    
    Args:
        db_manager: DatabaseManager instance
        collector: StockDataCollector instance
        batch_size: Number of stocks per batch
    """
    logger.info("📊 Starting price data refresh...")
    
    stocks = db_manager.get_all_stocks()
    total = len(stocks)
    success_count = 0
    fail_count = 0
    
    logger.info(f"Found {total} stocks to refresh")
    
    for i in range(0, total, batch_size):
        batch = stocks[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total // batch_size) + 1
        
        logger.info(f"\n📦 Batch {batch_num}/{total_batches}")
        
        for stock in batch:
            try:
                # Get latest price date in database
                latest_price = db_manager.get_latest_price(stock.id)
                
                if latest_price:
                    # Fetch data from latest date + 1 day to today
                    start_date = latest_price.date + timedelta(days=1)
                    logger.info(f"  [{stock.ticker}] Updating from {start_date.strftime('%Y-%m-%d')}...")
                else:
                    # No data, fetch last 5 years
                    start_date = datetime.now() - timedelta(days=5*365)
                    logger.info(f"  [{stock.ticker}] Fetching initial data (5 years)...")
                
                # Fetch new price data (use 'max' to get all available data, then filter)
                price_df = collector.fetch_price_history(stock.ticker, period='max')
                
                if price_df is not None and not price_df.empty:
                    # Filter to only new data (handle timezone-aware dates)
                    # Convert start_date to timezone-naive for comparison
                    if hasattr(price_df['date'].iloc[0], 'tz') and price_df['date'].iloc[0].tz is not None:
                        # DataFrame has timezone-aware dates, convert to naive
                        price_df['date'] = price_df['date'].dt.tz_localize(None)
                    
                    price_df = price_df[price_df['date'] >= start_date]
                    
                    if not price_df.empty:
                        db_manager.bulk_insert_prices(stock.id, price_df)
                        logger.info(f"    ✅ Added {len(price_df)} new price records")
                        success_count += 1
                    else:
                        logger.info(f"    ℹ️  No new data (already up to date)")
                        success_count += 1
                else:
                    logger.warning(f"    ⚠️  Failed to fetch price data")
                    fail_count += 1
                
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                logger.error(f"    ❌ Error refreshing {stock.ticker}: {e}")
                fail_count += 1
                continue
        
        logger.info(f"Progress: {min(i+batch_size, total)}/{total} ({min(i+batch_size, total)/total*100:.1f}%)")
    
    logger.info(f"\n✅ Price refresh complete: {success_count} success, {fail_count} failed")
    return success_count, fail_count


def refresh_fundamentals(db_manager, batch_size=50):
    """
    Refresh fundamental data using yfinance (free, no API limits).
    Updates quarterly metrics like P/E, ROE, debt ratios, etc.
    
    Args:
        db_manager: DatabaseManager instance
        batch_size: Number of stocks per batch
    """
    logger.info("\n📈 Starting fundamentals refresh (yfinance)...")
    
    stocks = db_manager.get_all_stocks()
    total = len(stocks)
    success_count = 0
    fail_count = 0
    
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
                    from data.schema import Fundamental
                    
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


def refresh_news_sentiment(db_manager, news_collector, sentiment_analyzer, max_stocks=500):
    """
    Refresh news and sentiment data.
    
    Args:
        db_manager: DatabaseManager instance
        news_collector: NewsCollector instance
        sentiment_analyzer: SentimentAnalyzer instance
        max_stocks: Maximum stocks to process (API limit)
    """
    logger.info("\n📰 Starting news & sentiment refresh...")
    
    stocks = db_manager.get_all_stocks()[:max_stocks]  # Limit to avoid API exhaustion
    total = len(stocks)
    success_count = 0
    fail_count = 0
    
    for i, stock in enumerate(stocks, 1):
        try:
            logger.info(f"[{i}/{total}] [{stock.ticker}] Fetching news...")
            
            # Fetch news from last 7 days
            articles = news_collector.fetch_stock_news(
                ticker=stock.ticker,
                company_name=stock.company_name or stock.ticker,
                days_back=7
            )
            
            if articles:
                for article in articles:
                    try:
                        # Analyze sentiment
                        sentiment = sentiment_analyzer.analyze_text(article['title'])
                        
                        # Save to database
                        db_manager.add_news_article(
                            stock_id=stock.id,
                            title=article['title'],
                            source=article.get('source', 'Unknown'),
                            url=article['url'],
                            published_at=article['published_at'],  # snake_case not camelCase
                            sentiment_score=sentiment['sentiment_score'],  # Match SentimentAnalyzer output
                            sentiment_label=sentiment['sentiment_label']  # Match SentimentAnalyzer output
                        )
                    except Exception as e:
                        logger.debug(f"      Article already exists or error: {e}")
                        continue
                
                logger.info(f"    ✅ Added {len(articles)} articles")
                success_count += 1
            else:
                logger.info(f"    ℹ️  No new articles")
                success_count += 1
            
            time.sleep(0.2)  # Rate limiting for NewsAPI
            
        except Exception as e:
            logger.error(f"    ❌ Error: {e}")
            fail_count += 1
            continue
    
    logger.info(f"\n✅ News refresh complete: {success_count} success, {fail_count} failed")
    return success_count, fail_count


def main():
    """Main daily refresh execution."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║            DAILY DATA REFRESH - SmartInvest Bot            ║
    ╚════════════════════════════════════════════════════════════╝
    
    This script will refresh:
    1. Stock prices (adds latest OHLCV data via yfinance)
    2. Fundamental metrics (P/E, ROE, debt via yfinance - FREE!)
    3. News articles & sentiment (last 7 days)
    
    Key features:
    • Preserves ALL historical data
    • Only adds NEW data points
    • 100% FREE (yfinance + NewsAPI free tier)
    • Safe to run daily via cron
    
    ⏱️  Estimated time: 15-20 minutes for 500 stocks
    
    """)
    
    start_time = datetime.now()
    logger.info(f"🚀 Starting daily refresh at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize
    logger.info("Initializing components...")
    
    db_manager = DatabaseManager(Config.DATABASE_URL)
    
    stock_collector = StockDataCollector(
        fmp_api_key=Config.FMP_API_KEY,
        finnhub_api_key=Config.FINNHUB_API_KEY
    )
    
    news_collector = NewsCollector(api_key=Config.NEWS_API_KEY)
    sentiment_analyzer = SentimentAnalyzer()
    
    # Stats
    total_stocks = len(db_manager.get_all_stocks())
    logger.info(f"📊 Database contains {total_stocks} stocks")
    
    if total_stocks == 0:
        logger.error("❌ No stocks in database! Run load_sp500.py first")
        return
    
    # Step 1: Refresh prices
    logger.info("\n" + "="*60)
    logger.info("STEP 1: REFRESH STOCK PRICES")
    logger.info("="*60)
    price_success, price_fail = refresh_stock_prices(db_manager, stock_collector)
    
    # Step 2: Refresh fundamentals (yfinance - free, no API key needed)
    logger.info("\n" + "="*60)
    logger.info("STEP 2: REFRESH FUNDAMENTALS (yfinance)")
    logger.info("="*60)
    fund_success, fund_fail = refresh_fundamentals(db_manager)
    
    # Step 3: Refresh news & sentiment
    logger.info("\n" + "="*60)
    logger.info("STEP 3: REFRESH NEWS & SENTIMENT")
    logger.info("="*60)
    news_success, news_fail = refresh_news_sentiment(
        db_manager, 
        news_collector, 
        sentiment_analyzer,
        max_stocks=min(total_stocks, 500)  # NewsAPI limit
    )
    
    # Step 4: Update performance trackers
    logger.info("\n" + "="*60)
    logger.info("STEP 4: UPDATE PERFORMANCE TRACKERS")
    logger.info("="*60)
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / 'update_performance.py')],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("✅ Performance tracking updated successfully")
            perf_success = True
        else:
            logger.error(f"❌ Performance tracking failed: {result.stderr}")
            perf_success = False
    except Exception as e:
        logger.error(f"❌ Error running performance update: {e}")
        perf_success = False
    
    # Step 5: Monitor exit signals
    logger.info("\n" + "="*60)
    logger.info("STEP 5: MONITOR EXIT SIGNALS")
    logger.info("="*60)
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / 'monitor_exit_signals.py')],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("✅ Exit signal monitoring completed successfully")
            exit_success = True
        else:
            logger.error(f"❌ Exit signal monitoring failed: {result.stderr}")
            exit_success = False
    except Exception as e:
        logger.error(f"❌ Error running exit monitoring: {e}")
        exit_success = False
    
    # Final summary
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║                    REFRESH COMPLETE!                       ║
    ╚════════════════════════════════════════════════════════════╝
    
    📊 Results:
       Prices:       {price_success} ✅  {price_fail} ❌
       Fundamentals: {fund_success} ✅  {fund_fail} ❌
       News:         {news_success} ✅  {news_fail} ❌
       Performance:  {'✅' if perf_success else '❌'}
       Exit Signals: {'✅' if exit_success else '❌'}
    
    ⏱️  Time: {elapsed/60:.1f} minutes
    🎯 Database: {total_stocks} stocks with fresh data
    
    Next steps:
    1. Run: python scripts/train_model_v2.py (retrain ML model)
    2. Bot will use updated data for recommendations
    3. Check /exits on Discord for active exit signals
    
    """)
    
    logger.info(f"✅ Daily refresh completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

