"""Debug date format mismatch"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from data.storage import DatabaseManager
from datetime import date, datetime

db = DatabaseManager(Config.DATABASE_URL)

# Get AAPL
stock = db.get_stock_by_ticker('AAPL')

# Try different date queries
test_date = date(2025, 10, 1)

print(f"Testing date query for {test_date}\n")

# Method 1: Direct query
price1 = db.get_price_at_date(stock.id, test_date)
print(f"get_price_at_date({test_date}): {price1}")

# Method 2: Get all October prices
from datetime import timedelta
prices = db.get_price_history(stock.id, start_date=test_date, end_date=test_date + timedelta(days=10))

print(f"\nAll prices from Oct 1-10:")
for p in prices[:10]:
    print(f"  Date: {p.date} (type: {type(p.date)}), Close: ${p.close:.2f}")
    
# Check if date matching works
if prices:
    first_price_date = prices[0].date
    print(f"\nFirst price date: {first_price_date}")
    print(f"Test date:        {test_date}")
    
    # Try converting
    if isinstance(first_price_date, datetime):
        print(f"\nDatabase stores datetime, query uses date!")
        print(f"Converted: {first_price_date.date()} == {test_date}? {first_price_date.date() == test_date}")
    else:
        print(f"\nDatabase stores date: {first_price_date == test_date}")

print("\n" + "="*60)
print("DIAGNOSIS:")
print("If database stores datetime but query uses date:")
print("  → Match will FAIL")
print("  → get_price_at_date() returns None")
print("  → Backtester uses entry_price as exit_price")
print("  → Return = 0%")

