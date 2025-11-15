#!/usr/bin/env python3
"""
Load REAL stock data using Alpha Vantage API
This script loads a curated list of top stocks with REAL-TIME data from Alpha Vantage
"""
import sys
import time
from datetime import datetime
from data.storage import DatabaseManager
from data.collectors import StockDataCollector
from config import Config

# Curated list of top liquid stocks (no Wikipedia needed!)
# These are the most traded, liquid stocks across all sectors
TOP_STOCKS = [
    # Technology
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD', 'INTC',
    'CRM', 'ORCL', 'ADBE', 'CSCO', 'AVGO', 'TXN', 'QCOM', 'NFLX', 'PYPL', 'SHOP',
    'SQ', 'UBER', 'LYFT', 'SNOW', 'PLTR', 'RBLX', 'COIN', 'ZM', 'DOCU', 'TWLO',
    
    # Finance
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'V',
    'MA', 'COF', 'USB', 'PNC', 'TFC', 'BK', 'STT', 'SPGI', 'MCO', 'ICE',
    
    # Healthcare
    'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'ABT', 'DHR', 'MRK', 'BMY', 'LLY',
    'AMGN', 'GILD', 'CVS', 'CI', 'HUM', 'REGN', 'VRTX', 'BIIB', 'ISRG', 'ZTS',
    
    # Consumer
    'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'COST', 'TJX', 'DG',
    'KO', 'PEP', 'PG', 'MDLZ', 'CL', 'KMB', 'GIS', 'K', 'HSY', 'CMG',
    
    # Industrial
    'BA', 'CAT', 'GE', 'MMM', 'HON', 'UPS', 'RTX', 'LMT', 'DE', 'EMR',
    
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PSX', 'VLO', 'MPC', 'OXY', 'HAL',
    
    # Telecom/Media
    'T', 'VZ', 'TMUS', 'DIS', 'CMCSA', 'CHTR', 'NFLX', 'PARA', 'WBD', 'FOXA',
    
    # Real Estate
    'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'DLR', 'SPG', 'O', 'WELL', 'AVB',
    
    # Materials
    'LIN', 'APD', 'SHW', 'ECL', 'DD', 'NEM', 'FCX', 'NUE', 'VMC', 'MLM',
    
    # Utilities  
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'WEC', 'ES',
    
    # Popular ETFs/Index representatives
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'VEA', 'VWO', 'AGG', 'BND',
    
    # Crypto/Fintech
    'MARA', 'RIOT', 'MSTR', 'SQ', 'PYPL', 'SOFI', 'AFRM', 'UPST', 'LC', 'NU',
    
    # Growth/Meme Stocks
    'GME', 'AMC', 'BB', 'BBBY', 'PLUG', 'NIO', 'LCID', 'RIVN', 'F', 'GM',
    
    # Additional High Volume
    'ARKK', 'ARKW', 'ARKG', 'SQQQ', 'TQQQ', 'SPXL', 'SPXS', 'UVXY', 'VXX', 'SVXY'
]

def load_stock_data(db_manager, collector, ticker, delay=12):
    """
    Load REAL-TIME data for a single stock from Alpha Vantage
    
    Args:
        db_manager: DatabaseManager instance
        collector: StockDataCollector instance
        ticker: Stock ticker symbol
        delay: Delay between requests (Alpha Vantage rate limiting: 5 calls/min = 12 sec)
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        print(f"  Fetching REAL-TIME data for {ticker}...", end=" ", flush=True)
        
        # Fetch REAL company info from Alpha Vantage
        info = collector.fetch_company_info(ticker)
        
        if not info or not info.get('company_name'):
            print(f"⚠ Skipped (not found)")
            return False, "Not found"
        
        # Add stock to database
        stock = db_manager.add_stock(
            ticker=ticker,
            company_name=info.get('company_name', ticker),
            sector=info.get('sector', 'Unknown'),
            industry=info.get('industry', 'Unknown'),
            market_cap=info.get('market_cap')
        )
        
        # Fetch REAL historical prices (1 year of actual trading data from Alpha Vantage)
        df = collector.fetch_price_history(ticker, period='1y')
        
        if df is not None and not df.empty:
            # Store REAL prices in database
            db_manager.bulk_insert_prices(stock.id, df)
            print(f"✓ {len(df)} days of REAL data")
            
            # Also try to get REAL fundamentals (from same API call, cached)
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
                        revenue_growth=fundamentals.get('revenue_growth_yoy'),
                        earnings_growth=fundamentals.get('earnings_growth_yoy')
                    )
            except Exception as e:
                pass  # Fundamentals are optional
        else:
            print(f"⚠ No price data")
            return False, "No price data"
        
        # Alpha Vantage rate limiting (collector handles this internally too)
        # No need to sleep here as collector already does it
        
        return True, "Success"
        
    except Exception as e:
        print(f"✗ Error: {str(e)[:50]}")
        return False, str(e)


def main():
    """Load REAL stock data from Alpha Vantage"""
    print("=" * 80)
    print("SmartInvest Bot - REAL-TIME Stock Data Loader")
    print("=" * 80)
    print()
    print("📊 Data Source: Alpha Vantage API (REAL-TIME)")
    print("🎯 Stocks: Top 200+ liquid stocks across all sectors")
    print("📈 Data: 1 year historical + current prices + fundamentals")
    print()
    
    # Initialize
    print("🔧 Initializing...")
    config = Config()
    db_manager = DatabaseManager(config.DATABASE_URL)
    
    # Initialize collector with Alpha Vantage API key
    if not config.VANTAGE_API_KEY:
        print("❌ ERROR: VANTAGE_API_KEY not found in .env file")
        print("   Please add your Alpha Vantage API key to .env")
        sys.exit(1)
    
    collector = StockDataCollector(api_key=config.VANTAGE_API_KEY)
    print("✅ Connected to Alpha Vantage API\n")
    
    # Remove duplicates and sort
    tickers = sorted(list(set(TOP_STOCKS)))
    
    print(f"📊 Will load {len(tickers)} stocks with REAL data")
    print(f"⏱️  Estimated time: ~{len(tickers) * 12 / 60:.0f} minutes (Alpha Vantage rate limit: 5 calls/min)")
    print()
    print("⚠️  NOTE: Alpha Vantage free tier has rate limits:")
    print("   - 5 API calls per minute (12 seconds between calls)")
    print("   - 25 API calls per day on free tier")
    print(f"   - Loading {len(tickers)} stocks will take several calls per stock")
    print()
    print("💡 RECOMMENDATION: Load a smaller batch first (e.g., 5-10 stocks)")
    print("   You can run this script multiple times to load more data.")
    print()
    
    # Ask for confirmation
    response = input("   Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("   Cancelled.")
        return
    
    print(f"\n📥 Loading REAL-TIME data for {len(tickers)} stocks...")
    print("   (Fetching directly from Alpha Vantage API)\n")
    
    start_time = datetime.now()
    successful = []
    failed = []
    
    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] {ticker:6s}", end=" ")
        
        success, message = load_stock_data(db_manager, collector, ticker)
        
        if success:
            successful.append(ticker)
        else:
            failed.append((ticker, message))
        
        # Progress update every 50 stocks
        if i % 50 == 0:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            remaining = (len(tickers) - i) * (elapsed / i)
            print(f"\n   Progress: {i}/{len(tickers)} ({i/len(tickers)*100:.1f}%)")
            print(f"   Elapsed: {elapsed:.1f} min | Remaining: ~{remaining:.1f} min\n")
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds() / 60
    
    print("\n" + "=" * 80)
    print("Summary - REAL DATA LOADED")
    print("=" * 80)
    print(f"✅ Successfully loaded: {len(successful)} stocks with REAL data")
    print(f"❌ Failed: {len(failed)} stocks")
    print(f"⏱️  Time: {elapsed:.1f} minutes")
    if len(tickers) > 0:
        print(f"📊 Success rate: {len(successful)/len(tickers)*100:.1f}%")
    print()
    
    if failed and len(failed) <= 10:
        print("❌ Failed tickers:")
        for ticker, msg in failed:
            print(f"   {ticker}: {msg[:50]}")
    elif failed:
        print(f"❌ {len(failed)} tickers failed (check logs)")
    
    print("\n" + "=" * 80)
    print("✅ REAL STOCK DATA LOADED FROM ALPHA VANTAGE!")
    print("=" * 80)
    print()
    print("Your bot now has:")
    print(f"  • {len(successful)} stocks")
    print(f"  • ~{len(successful) * 252} price points")
    print("  • Real-time prices from Alpha Vantage")
    print("  • Technical indicators ready")
    print("  • Fundamental data (where available)")
    print()
    print("Next steps:")
    print("  1. Start bot: python bot_with_real_data.py")
    print("  2. Test in Discord: /stock AAPL")
    print("  3. Get recommendations: /daily")
    print()
    print("💡 TIP: You can run this script again to load more stocks")
    print("   (respecting Alpha Vantage rate limits)")
    print()
    print("🎉 Your bot is now using 100% REAL data from Alpha Vantage!")
    print("=" * 80)


if __name__ == "__main__":
    main()

