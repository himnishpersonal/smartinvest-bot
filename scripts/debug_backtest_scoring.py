"""Debug why backtester returns 0 recommendations"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from data.storage import DatabaseManager
from models.backtester import Backtester
from datetime import date, timedelta
import joblib

# Setup
db = DatabaseManager(Config.DATABASE_URL)
ml_model_data = joblib.load('models/saved_models/model_latest.pkl')
ml_model = ml_model_data.get('model') if isinstance(ml_model_data, dict) else ml_model_data

# Feature calculator
from bot_with_real_data import SmartInvestBot
bot = SmartInvestBot()

# Create backtester
backtester = Backtester(db, ml_model, bot._calculate_backtest_features)

# Try October 1
test_date = date(2025, 10, 1)
print(f"Testing {test_date}...\n")

# Check what price data is available
stock = db.get_stock_by_ticker('AAPL')
start_date = test_date - timedelta(days=90)
end_date = test_date - timedelta(days=1)

print(f"Looking for prices from {start_date} to {end_date}")
prices = db.get_price_history(stock.id, start_date=start_date, end_date=end_date)
print(f"Found {len(prices)} price records")

if len(prices) > 0:
    dates = [p.date.date() for p in prices]
    print(f"  First: {min(dates)}")
    print(f"  Last:  {max(dates)}")

# Now score all stocks
print(f"\nCalling backtester.score_stocks_at_date({test_date})...")
recommendations = backtester.score_stocks_at_date(test_date)

print(f"Result: {len(recommendations)} recommendations")

if len(recommendations) > 0:
    print("\nTop 5:")
    for rec in recommendations[:5]:
        print(f"  {rec['ticker']}: {rec['score']}")
else:
    print("\n❌ NO RECOMMENDATIONS!")
    print("\nPossible causes:")
    print("  1. Insufficient price data (need >= 30 days)")
    print("  2. ML model failing")
    print("  3. Feature calculation errors")

