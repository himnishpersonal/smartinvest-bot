"""Check which stocks have complete October data"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from data.storage import DatabaseManager
from datetime import date

db = DatabaseManager(Config.DATABASE_URL)

# Get all stocks
stocks = db.get_all_stocks()

# Check October 1-31 coverage
october_start = date(2025, 10, 1)
october_end = date(2025, 10, 31)

stocks_with_full_data = []
stocks_with_partial_data = []
stocks_with_no_data = []

print(f"Checking October coverage for {len(stocks)} stocks...\n")

for stock in stocks[:50]:  # Check first 50 for speed
    prices = db.get_price_history(stock.id, start_date=october_start, end_date=october_end)
    
    if len(prices) >= 20:  # At least 20 trading days
        stocks_with_full_data.append(stock.ticker)
    elif len(prices) > 0:
        stocks_with_partial_data.append(stock.ticker)
    else:
        stocks_with_no_data.append(stock.ticker)

print(f"Results (first 50 stocks):")
print(f"  ✓ Full data (20+ days):    {len(stocks_with_full_data)}")
print(f"  ⚠ Partial data (1-19 days): {len(stocks_with_partial_data)}")
print(f"  ✗ No data:                  {len(stocks_with_no_data)}")

if stocks_with_no_data:
    print(f"\nStocks with NO October data:")
    print(f"  {', '.join(stocks_with_no_data[:20])}")
    if len(stocks_with_no_data) > 20:
        print(f"  ... and {len(stocks_with_no_data) - 20} more")

print("\n" + "="*60)
print("DIAGNOSIS:")
if len(stocks_with_no_data) > 20:
    print("❌ Many stocks missing October data!")
    print("   This is why returns are 0%")
    print("\nSOLUTION:")
    print("   Option 1: Run daily_refresh.py to fill gaps")
    print("   Option 2: Backtest OLDER period (Aug-Sep)")
    print("   Option 3: Use only stocks with full data")
else:
    print("✓ Most stocks have October data")
    print("  Returns should work for stocks with data")

