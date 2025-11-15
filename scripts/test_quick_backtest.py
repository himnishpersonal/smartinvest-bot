"""Quick 30-day backtest to test execution"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from data.storage import DatabaseManager
from models.backtester import Backtester, PortfolioSimulator
from datetime import date
import joblib

# Setup
print("Setting up quick backtest...\n")
db = DatabaseManager(Config.DATABASE_URL)
ml_model_dict = joblib.load('models/saved_models/model_latest.pkl')
ml_model = ml_model_dict.get('model') if isinstance(ml_model_dict, dict) else ml_model_dict

# Feature calculator
import numpy as np
def calculate_features(price_df, articles):
    if len(price_df) < 30:
        return None
    closes = price_df['close'].values
    volumes = price_df['volume'].values
    return_5d = (closes[-1] - closes[-6]) / closes[-6] if len(closes) >= 6 else 0
    return_10d = (closes[-1] - closes[-11]) / closes[-11] if len(closes) >= 11 else 0
    return_20d = (closes[-1] - closes[-21]) / closes[-21] if len(closes) >= 21 else 0
    momentum = sum([1 if closes[i] > closes[i-1] else -1 for i in range(1, len(closes))]) / len(closes)
    avg_volume = sum(volumes) / len(volumes)
    volume_trend = (volumes[-1] - avg_volume) / avg_volume if avg_volume > 0 else 0
    if articles:
        sentiment_scores = [a.sentiment_score for a in articles if a.sentiment_score is not None]
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            sentiment_positive = sum(1 for s in sentiment_scores if s > 0.3) / len(sentiment_scores)
            sentiment_negative = sum(1 for s in sentiment_scores if s < -0.3) / len(sentiment_scores)
        else:
            avg_sentiment = sentiment_positive = sentiment_negative = 0
    else:
        avg_sentiment = sentiment_positive = sentiment_negative = 0
    return {
        'return_5d': return_5d, 'return_10d': return_10d, 'return_20d': return_20d,
        'momentum': momentum, 'volume_trend': volume_trend, 'avg_sentiment': avg_sentiment,
        'sentiment_positive': sentiment_positive, 'sentiment_negative': sentiment_negative
    }

# Create components
backtester = Backtester(db, ml_model, calculate_features)
simulator = PortfolioSimulator(starting_capital=10000, hold_days=5, max_positions=10)

# Run SHORT backtest (Oct 1-31)
start_date = date(2025, 10, 1)
end_date = date(2025, 10, 31)

print(f"Running backtest: {start_date} to {end_date}")
print("This should take ~30 seconds...\n")

results = simulator.run_backtest(backtester, start_date, end_date)

print(f"\n{'='*60}")
print("RESULTS")
print('='*60)
print(f"Total trades: {len(results['closed_trades'])}")
print(f"Starting capital: ${results['starting_capital']:,.0f}")
print(f"Ending value: ${results['final_value']:,.0f}")

if results['closed_trades']:
    print("\nTrades executed:")
    for trade in results['closed_trades'][:10]:
        print(f"  {trade['ticker']:5s} {trade['entry_date']} -> {trade['exit_date']}: {trade['pnl_pct']:+.2f}%")
else:
    print("\n❌ NO TRADES EXECUTED!")
    print("\nDebug info:")
    print(f"  - Equity curve points: {len(results['equity_curve'])}")
    if results['equity_curve']:
        print(f"  - First day value: ${results['equity_curve'][0]['value']:,.0f}")
        print(f"  - Last day value: ${results['equity_curve'][-1]['value']:,.0f}")

