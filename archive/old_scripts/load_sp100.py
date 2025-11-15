#!/usr/bin/env python3
"""
Load S&P 100 stocks - perfect for getting 100+ stocks for ML training
"""
import sys
from data.storage import DatabaseManager
from data.collectors import StockDataCollector, get_sp100_tickers
from config import Config

print("=" * 60)
print("Loading S&P 100 Stocks")
print("=" * 60)
print()

# Initialize
config = Config()
db_manager = DatabaseManager(config.DATABASE_URL)

# Create tables if they don't exist
print("Ensuring database tables exist...")
from data.schema import Base
Base.metadata.create_all(db_manager.engine)
print("✅ Tables ready")
print()

# Check for API keys
if not config.FMP_API_KEY:
    print("❌ ERROR: FMP_API_KEY not found in .env file")
    sys.exit(1)

collector = StockDataCollector(
    fmp_api_key=config.FMP_API_KEY,
    finnhub_api_key=config.FINNHUB_API_KEY
)
print("✅ Connected to hybrid data sources")

# Get S&P 100 tickers
sp100_tickers = get_sp100_tickers()
print(f"📊 S&P 100 contains {len(sp100_tickers)} stocks")
print()

# Check which stocks are already loaded
existing_stocks = db_manager.get_all_stocks()
existing_tickers = {stock.ticker for stock in existing_stocks}
new_tickers = [t for t in sp100_tickers if t not in existing_tickers]

print(f"Already in database: {len(existing_tickers)} stocks")
print(f"New stocks to load: {len(new_tickers)} stocks")
print()

if len(new_tickers) == 0:
    print("✅ All S&P 100 stocks already loaded!")
    sys.exit(0)

# Estimate time and API calls
estimated_time = len(new_tickers) * 3  # 3 seconds per stock
estimated_calls = len(new_tickers) * 2  # 2 calls per stock (company info + price history)

print(f"⏱️  Estimated time: ~{estimated_time // 60} minutes {estimated_time % 60} seconds")
print(f"📞 API calls needed: ~{estimated_calls} (FMP limit: 250/day)")
print()

if estimated_calls > 200:
    print("⚠️  WARNING: This will use most of your daily FMP API limit")
    print("   Consider loading in batches over multiple days")
    print()

# Ask for confirmation
response = input("Proceed with loading? (yes/no): ").strip().lower()
if response not in ['yes', 'y']:
    print("Cancelled.")
    sys.exit(0)

print()
print("=" * 60)
print(f"Loading {len(new_tickers)} stocks...")
print("=" * 60)
print()

successful = 0
failed = 0
failed_tickers = []

for i, ticker in enumerate(new_tickers, 1):
    try:
        print(f"[{i}/{len(new_tickers)}] {ticker}...", end=" ", flush=True)
        
        # Get company info
        info = collector.fetch_company_info(ticker)
        
        if not info:
            print("⚠ No company info - skipping")
            failed += 1
            failed_tickers.append(ticker)
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
            print("⚠ No price data")
            failed += 1
            failed_tickers.append(ticker)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        break
    except Exception as e:
        error_msg = str(e)[:50]
        print(f"✗ Error: {error_msg}")
        failed += 1
        failed_tickers.append(ticker)

print()
print("=" * 60)
print(f"✅ Successfully loaded: {successful} stocks")
print(f"❌ Failed: {failed} stocks")
print("=" * 60)

if failed_tickers:
    print()
    print("Failed tickers:", ", ".join(failed_tickers))

# Show final stats
all_stocks = db_manager.get_all_stocks()
print()
print(f"📊 Total stocks in database: {len(all_stocks)}")

# Show sector distribution
sectors = {}
for stock in all_stocks:
    sector = stock.sector or 'Unknown'
    sectors[sector] = sectors.get(sector, 0) + 1

print()
print("Sector Distribution:")
for sector, count in sorted(sectors.items(), key=lambda x: -x[1]):
    print(f"  {sector}: {count} stocks")

print()
if successful > 0:
    print("🎉 Success! Your bot now has more data for better ML training!")
    print()
    print("Next steps:")
    print("1. Train ML model: python scripts/train_model.py")
    print("2. Test bot: python bot_with_real_data.py")
    print("3. Try Discord command: /daily")

