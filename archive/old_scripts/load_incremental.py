#!/usr/bin/env python3
"""
Load stocks incrementally - add 10-50 stocks at a time to stay under API limits
Perfect for building to 200+ stocks over several days
"""
import sys
from data.storage import DatabaseManager
from data.collectors import StockDataCollector, get_sp500_tickers
from config import Config

print("=" * 60)
print("Incremental Stock Loader")
print("=" * 60)
print()

# Initialize
config = Config()
db_manager = DatabaseManager(config.DATABASE_URL)

if not config.FMP_API_KEY:
    print("❌ ERROR: FMP_API_KEY not found in .env file")
    sys.exit(1)

collector = StockDataCollector(
    fmp_api_key=config.FMP_API_KEY,
    finnhub_api_key=config.FINNHUB_API_KEY
)

# Get all available tickers
sp500_tickers = get_sp500_tickers()
print(f"📊 Total stocks available: {len(sp500_tickers)}")

# Check what's already loaded
existing_stocks = db_manager.get_all_stocks()
existing_tickers = {stock.ticker for stock in existing_stocks}
remaining_tickers = [t for t in sp500_tickers if t not in existing_tickers]

print(f"✅ Already loaded: {len(existing_tickers)} stocks")
print(f"📋 Remaining: {len(remaining_tickers)} stocks")
print()

if len(remaining_tickers) == 0:
    print("✅ All available stocks already loaded!")
    sys.exit(0)

# Ask how many to load
print("How many stocks to load today?")
print("  Recommendation: 10-50 stocks per day")
print("  (uses ~20-100 API calls out of 250/day limit)")
print()

try:
    batch_size = int(input("Number of stocks to load (or 'q' to quit): ").strip())
    if batch_size <= 0:
        print("Invalid number")
        sys.exit(1)
    if batch_size > len(remaining_tickers):
        batch_size = len(remaining_tickers)
        print(f"Adjusted to {batch_size} (all remaining stocks)")
except (ValueError, KeyboardInterrupt):
    print("Cancelled")
    sys.exit(0)

# Select batch to load
tickers_to_load = remaining_tickers[:batch_size]

estimated_time = batch_size * 3
estimated_calls = batch_size * 2

print()
print(f"⏱️  Estimated time: ~{estimated_time // 60} minutes {estimated_time % 60} seconds")
print(f"📞 API calls: ~{estimated_calls} / 250 daily limit")
print()

if estimated_calls > 230:
    print("⚠️  WARNING: Close to daily API limit!")
    print()

response = input("Proceed? (yes/no): ").strip().lower()
if response not in ['yes', 'y']:
    print("Cancelled.")
    sys.exit(0)

print()
print("=" * 60)
print(f"Loading {len(tickers_to_load)} stocks...")
print("=" * 60)
print()

successful = 0
failed = 0

for i, ticker in enumerate(tickers_to_load, 1):
    try:
        print(f"[{i}/{len(tickers_to_load)}] {ticker}...", end=" ", flush=True)
        
        # Get company info
        info = collector.fetch_company_info(ticker)
        
        if not info:
            print("⚠ Skip")
            failed += 1
            continue
        
        # Add to database
        stock = db_manager.add_stock(
            ticker=ticker,
            company_name=info.get('company_name', ticker),
            sector=info.get('sector', 'Unknown'),
            industry=info.get('industry', 'Unknown'),
            market_cap=info.get('market_cap')
        )
        
        # Get price history
        df = collector.fetch_price_history(ticker, period='1y')
        
        if df is not None and not df.empty:
            db_manager.bulk_insert_prices(stock.id, df)
            print(f"✓ {len(df)} days")
            successful += 1
        else:
            print("⚠ No data")
            failed += 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        break
    except Exception as e:
        print(f"✗ {str(e)[:30]}")
        failed += 1

print()
print("=" * 60)
print(f"✅ Successfully loaded: {successful} stocks")
print(f"❌ Failed: {failed} stocks")

all_stocks = db_manager.get_all_stocks()
print(f"📊 Total in database: {len(all_stocks)} stocks")
print()
print(f"📋 Remaining available: {len(remaining_tickers) - batch_size} stocks")
print("=" * 60)

if successful > 0:
    print()
    print("🎉 Progress made! Run this script daily to add more stocks.")
    print()
    print(f"Goal: {len(all_stocks)}/200+ stocks")

