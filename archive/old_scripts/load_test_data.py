#!/usr/bin/env python3
"""
Quick script to load test stocks using FMP + Finnhub hybrid
Run this to get your bot working with real data!
"""
import sys
from data.storage import DatabaseManager
from data.collectors import StockDataCollector
from config import Config

print("=" * 60)
print("Loading Test Stock Data (FMP + Finnhub Hybrid)")
print("=" * 60)
print()

# Initialize
config = Config()
db_manager = DatabaseManager(config.DATABASE_URL)

# Check for API keys
if not config.FMP_API_KEY:
    print("❌ ERROR: FMP_API_KEY not found in .env file")
    print("   Please add your FMP API key to .env")
    print("   Get one free at: https://site.financialmodelingprep.com/developer/docs")
    sys.exit(1)

if not config.FINNHUB_API_KEY:
    print("⚠️  WARNING: FINNHUB_API_KEY not found (real-time backup unavailable)")

collector = StockDataCollector(
    fmp_api_key=config.FMP_API_KEY,
    finnhub_api_key=config.FINNHUB_API_KEY
)
print("✅ Connected to FMP API (primary) + Finnhub (backup)")

# Test stocks - organized by batch
BATCH_1 = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']  # Already loaded
BATCH_2 = ['META', 'AMZN', 'NFLX', 'JPM', 'BAC']
BATCH_3 = ['WMT', 'JNJ', 'UNH', 'V', 'MA']
BATCH_4 = ['HD', 'DIS', 'KO', 'PEP', 'PG']
BATCH_5 = ['XOM', 'CVX', 'AMD', 'INTC', 'CSCO']

print("Available batches:")
print("  1. BATCH_1 (5 stocks) - Tech leaders")
print("  2. BATCH_2 (5 stocks) - Tech + Finance")
print("  3. BATCH_3 (5 stocks) - Healthcare + Payments")
print("  4. BATCH_4 (5 stocks) - Consumer staples")
print("  5. BATCH_5 (5 stocks) - Energy + Tech")
print("  6. ALL (25 stocks) - All batches")
print()

batch_choice = input("Which batch to load? (1-6): ").strip()

if batch_choice == '1':
    test_stocks = BATCH_1
elif batch_choice == '2':
    test_stocks = BATCH_2
elif batch_choice == '3':
    test_stocks = BATCH_3
elif batch_choice == '4':
    test_stocks = BATCH_4
elif batch_choice == '5':
    test_stocks = BATCH_5
elif batch_choice == '6':
    test_stocks = BATCH_1 + BATCH_2 + BATCH_3 + BATCH_4 + BATCH_5
else:
    print("Invalid choice, using BATCH_2")
    test_stocks = BATCH_2

print(f"\nLoading {len(test_stocks)} stocks...")
print("⏱️  This will take ~{} seconds (FMP: 250 calls/day)".format(len(test_stocks) * 2))
print()

successful = 0
failed = 0

for i, ticker in enumerate(test_stocks, 1):
    try:
        print(f"[{i}/{len(test_stocks)}] {ticker}...", end=" ", flush=True)
        
        # Get company info
        info = collector.fetch_company_info(ticker)
        
        # Add to database
        stock = db_manager.add_stock(
            ticker=ticker,
            company_name=info.get('company_name', ticker),
            sector=info.get('sector', 'Technology'),
            industry=info.get('industry', 'Software'),
            market_cap=info.get('market_cap')
        )
        
        # Get price history
        df = collector.fetch_price_history(ticker, period='1y')
        
        if df is not None and not df.empty:
            db_manager.bulk_insert_prices(stock.id, df)
            print(f"✓ Loaded {len(df)} days of data")
            successful += 1
        else:
            print("⚠ No price data")
            failed += 1
            
    except Exception as e:
        print(f"✗ Error: {str(e)[:50]}")
        failed += 1

print()
print("=" * 60)
print(f"✅ Successfully loaded: {successful} stocks")
print(f"❌ Failed: {failed} stocks")
print("=" * 60)
print()

if successful > 0:
    print("🎉 Success! Your bot now has data!")
    print()
    print("Next steps:")
    print("1. Make sure bot is running: python bot_with_real_data.py")
    print("2. Go to Discord")
    print("3. Try: /stock AAPL")
    print("4. Try: /daily")
    print()
else:
    print("❌ No stocks loaded. Check your internet connection.")
    print("   Or you may have hit FMP rate limits.")
    print("   Free tier: 250 calls per day (be mindful!)")

