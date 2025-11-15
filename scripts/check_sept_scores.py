"""Check what scores stocks are actually getting in September"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from data.storage import DatabaseManager
from models.backtester import Backtester
from datetime import date
import joblib
import numpy as np

# Load everything
db = DatabaseManager(Config.DATABASE_URL)
ml_model_data = joblib.load('models/saved_models/model_latest.pkl')
ml_model = ml_model_data.get('model') if isinstance(ml_model_data, dict) else ml_model_data

# Feature calculation function (imported from bot)
from bot_with_real_data import SmartInvestBot
bot = SmartInvestBot()

# Create backtester
backtester = Backtester(db, ml_model, bot._calculate_backtest_features)

# Check scores for Sept 15 (random weekday)
test_date = date(2025, 9, 15)
print(f"Scoring stocks for {test_date}...\n")

recommendations = backtester.score_stocks_at_date(test_date)

if recommendations:
    print(f"Total stocks scored: {len(recommendations)}")
    
    # Show score distribution
    scores = [r['score'] for r in recommendations]
    print(f"\nScore statistics:")
    print(f"  Min:    {min(scores):.1f}")
    print(f"  Max:    {max(scores):.1f}")
    print(f"  Median: {np.median(scores):.1f}")
    print(f"  Mean:   {np.mean(scores):.1f}")
    
    # Show distribution
    for threshold in [50, 55, 60, 65, 70, 75]:
        count = len([s for s in scores if s >= threshold])
        pct = (count / len(scores)) * 100
        print(f"  Scores >= {threshold}: {count} ({pct:.1f}%)")
    
    # Show top 10
    print(f"\nTop 10 stocks:")
    for i, rec in enumerate(recommendations[:10], 1):
        print(f"  {i}. {rec['ticker']:6s} score: {rec['score']:.0f}")
else:
    print("❌ No stocks scored!")

