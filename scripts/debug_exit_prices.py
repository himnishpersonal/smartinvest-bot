"""Debug why returns are 0% - check exit price availability"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from data.storage import DatabaseManager
from datetime import date, timedelta

db = DatabaseManager(Config.DATABASE_URL)

# Check a few stocks from October trades
test_cases = [
    ('SEDG', date(2025, 10, 1), date(2025, 10, 6)),  # Entry -> Exit
    ('LRCX', date(2025, 10, 1), date(2025, 10, 6)),
    ('TSLA', date(2025, 10, 1), date(2025, 10, 6)),
]

print("Checking exit price availability...\n")

for ticker, entry_date, exit_date in test_cases:
    stock = db.get_stock_by_ticker(ticker)
    if not stock:
        print(f"{ticker}: Stock not found")
        continue
    
    entry_price_obj = db.get_price_at_date(stock.id, entry_date)
    exit_price_obj = db.get_price_at_date(stock.id, exit_date)
    
    print(f"{ticker}:")
    print(f"  Entry {entry_date}: ${entry_price_obj.close:.2f}" if entry_price_obj else f"  Entry {entry_date}: NOT FOUND")
    print(f"  Exit  {exit_date}: ${exit_price_obj.close:.2f}" if exit_price_obj else f"  Exit  {exit_date}: NOT FOUND")
    
    if entry_price_obj and exit_price_obj:
        pnl_pct = ((exit_price_obj.close - entry_price_obj.close) / entry_price_obj.close) * 100
        print(f"  Return: {pnl_pct:+.2f}%")
    else:
        print(f"  Return: Cannot calculate (missing price data)")
    print()

# Check what's our latest date in database
print("=" * 60)
print("Checking database coverage...")
sample_stock = db.get_stock_by_ticker('AAPL')
if sample_stock:
    prices = db.get_price_history(sample_stock.id, start_date=date(2025, 10, 1), end_date=date(2025, 11, 11))
    if prices:
        dates = [p.date for p in prices]
        print(f"\nAAPL price data range:")
        print(f"  First date: {min(dates)}")
        print(f"  Last date:  {max(dates)}")
        print(f"  Total days: {len(dates)}")
        
        # Check for gaps
        all_dates = set(dates)
        expected_dates = []
        current = min(dates)
        while current <= max(dates):
            if current.weekday() < 5:  # Weekdays only
                expected_dates.append(current)
            current += timedelta(days=1)
        
        missing_dates = [d for d in expected_dates if d not in all_dates]
        if missing_dates:
            print(f"\n  ⚠️  Missing dates: {len(missing_dates)}")
            print(f"      Examples: {missing_dates[:5]}")
        else:
            print(f"\n  ✓ No gaps in price data")

print("\n" + "=" * 60)
print("CONCLUSION:")
print("If exit prices are missing → Returns will be 0%")
print("Solution: Run daily_refresh.py to update prices")

