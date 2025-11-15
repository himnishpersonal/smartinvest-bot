"""Check if we have Sept 14 data"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from data.storage import DatabaseManager
from datetime import date, timedelta

db = DatabaseManager(Config.DATABASE_URL)

# Get AAPL
stock = db.get_stock_by_ticker('AAPL')

# Check September range
sept_start = date(2025, 9, 1)
sept_end = date(2025, 9, 20)

prices = db.get_price_history(stock.id, start_date=sept_start, end_date=sept_end)

print("AAPL prices in early September:")
for p in prices:
    print(f"  {p.date.date()}: ${p.close:.2f}")

if not prices:
    print("❌ NO DATA FOUND!")
elif len(prices) < 10:
    print(f"\n⚠️  Only {len(prices)} days of data - insufficient for scoring")
else:
    print(f"\n✓ {len(prices)} days of data available")

# Check the specific cutoff used by backtester
target_date = date(2025, 9, 15)
cutoff_date = target_date - timedelta(days=1)
print(f"\nBacktester looks for data BEFORE {target_date}")
print(f"Cutoff: {cutoff_date}")

prices_before = [p for p in prices if p.date.date() <= cutoff_date]
print(f"Prices on or before {cutoff_date}: {len(prices_before)}")

