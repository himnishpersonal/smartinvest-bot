#!/usr/bin/env python3
"""
ML Model Training Script - Rebuilt Version
Works with actual available data in database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from config import Config
from data.storage import DatabaseManager
from data.schema import Stock, StockPrice, NewsArticle
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

print("=" * 80)
print("SmartInvest Bot - ML Model Training (Rebuilt)")
print("=" * 80)
print()

config = Config()
db_manager = DatabaseManager(config.DATABASE_URL)

# Step 1: Analyze what data we actually have
print("📊 Step 1: Analyzing available data...")
print()

stocks = db_manager.get_all_stocks()
print(f"   Total stocks: {len(stocks)}")

# Check which stocks have price data
stocks_with_data = []

with db_manager.get_session() as session:
    for stock in stocks:
        price_count = session.query(StockPrice).filter_by(stock_id=stock.id).count()
        news_count = session.query(NewsArticle).filter_by(stock_id=stock.id).count()
        
        if price_count > 0:
            stocks_with_data.append({
                'stock': stock,
                'price_count': price_count,
                'news_count': news_count
            })

print(f"   Stocks with price data: {len(stocks_with_data)}")
print(f"   Stocks without price data: {len(stocks) - len(stocks_with_data)}")
print()

if len(stocks_with_data) == 0:
    print("❌ ERROR: No stocks have price data!")
    print()
    print("This means the database needs to be reloaded.")
    print()
    print("SOLUTION:")
    print("  1. Delete the database: rm smartinvest_dev.db")
    print("  2. Reload stocks: python load_sp100.py")
    print("  3. Reload news: python scripts/fetch_news_sentiment.py")
    print("  4. Then retry training")
    print()
    sys.exit(1)

# Sample some stocks to show data
print("   Sample stocks with data:")
for item in stocks_with_data[:5]:
    stock = item['stock']
    print(f"     {stock.ticker}: {item['price_count']} prices, {item['news_count']} news")
print()

# Step 2: Prepare simple training data (no complex features for now)
print("📊 Step 2: Preparing training dataset...")
print("   (Using simplified approach: price momentum + news sentiment)")
print()

X_list = []
y_list = []
metadata_list = []

for item in stocks_with_data:
    stock = item['stock']
    
    try:
        # Get prices directly from database
        with db_manager.get_session() as session:
            prices = session.query(StockPrice).filter_by(stock_id=stock.id).order_by(StockPrice.date).all()
            
            if len(prices) < 30:  # Need at least 30 days
                continue
            
            # Calculate simple features from last 30 days
            recent_prices = prices[-30:]
            closes = [p.close for p in recent_prices]
            volumes = [p.volume for p in recent_prices]
            
            # Feature 1: 5-day return
            return_5d = (closes[-1] - closes[-6]) / closes[-6] if len(closes) >= 6 else 0
            
            # Feature 2: 10-day return
            return_10d = (closes[-1] - closes[-11]) / closes[-11] if len(closes) >= 11 else 0
            
            # Feature 3: 20-day return
            return_20d = (closes[-1] - closes[-21]) / closes[-21] if len(closes) >= 21 else 0
            
            # Feature 4: Price momentum (simple)
            momentum = sum([1 if closes[i] > closes[i-1] else -1 for i in range(1, len(closes))]) / len(closes)
            
            # Feature 5: Volume trend
            avg_volume = sum(volumes) / len(volumes)
            volume_trend = (volumes[-1] - avg_volume) / avg_volume if avg_volume > 0 else 0
            
            # Feature 6-8: News sentiment
            news_articles = session.query(NewsArticle).filter_by(stock_id=stock.id).order_by(NewsArticle.published_at.desc()).limit(20).all()
            
            if news_articles:
                sentiment_scores = [a.sentiment_score for a in news_articles if a.sentiment_score is not None]
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
                sentiment_positive = sum(1 for s in sentiment_scores if s > 0.3) / len(sentiment_scores) if sentiment_scores else 0
                sentiment_negative = sum(1 for s in sentiment_scores if s < -0.3) / len(sentiment_scores) if sentiment_scores else 0
            else:
                avg_sentiment = 0
                sentiment_positive = 0
                sentiment_negative = 0
            
            # Create feature vector
            features = [
                return_5d,
                return_10d,
                return_20d,
                momentum,
                volume_trend,
                avg_sentiment,
                sentiment_positive,
                sentiment_negative
            ]
            
            # Label: Will price go up in next 5 days?
            # For now, use historical data (last 5 days vs 10 days ago)
            if len(prices) >= 15:
                price_10d_ago = prices[-10].close
                price_5d_ago = prices[-5].close
                label = 1 if price_5d_ago > price_10d_ago else 0
            else:
                continue
            
            X_list.append(features)
            y_list.append(label)
            metadata_list.append({
                'ticker': stock.ticker,
                'date': prices[-1].date
            })
            
    except Exception as e:
        logger.error(f"Error processing {stock.ticker}: {e}")
        continue

if len(X_list) == 0:
    print("❌ ERROR: Could not prepare any training data!")
    sys.exit(1)

X = np.array(X_list)
y = np.array(y_list)

print(f"   ✅ Dataset prepared:")
print(f"      Samples: {len(X)}")
print(f"      Features: {X.shape[1]}")
print(f"      Positive labels: {sum(y)} ({sum(y)/len(y)*100:.1f}%)")
print(f"      Negative labels: {len(y)-sum(y)} ({(len(y)-sum(y))/len(y)*100:.1f}%)")
print()

# Step 3: Train simple XGBoost model
print("🤖 Step 3: Training XGBoost model...")

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

# Split data (time-series aware: last 20% for testing)
split_idx = int(len(X) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

print(f"   Training samples: {len(X_train)}")
print(f"   Test samples: {len(X_test)}")
print()

# Train model
model = XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    random_state=42,
    eval_metric='logloss'
)

model.fit(X_train, y_train, verbose=False)

print("   ✅ Model trained!")
print()

# Step 4: Evaluate
print("📊 Step 4: Evaluating model...")
print()

y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)

try:
    roc_auc = roc_auc_score(y_test, y_pred_proba)
except:
    roc_auc = 0.5

print(f"   Accuracy:  {accuracy:.2%}")
print(f"   Precision: {precision:.2%}")
print(f"   Recall:    {recall:.2%}")
print(f"   F1 Score:  {f1:.2%}")
print(f"   ROC AUC:   {roc_auc:.3f}")
print()

# Feature importance
print("   Top features:")
feature_names = ['5d_return', '10d_return', '20d_return', 'momentum', 'volume_trend', 
                 'avg_sentiment', 'sentiment_pos', 'sentiment_neg']
importances = model.feature_importances_
for name, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True):
    print(f"     {name:20s}: {imp:.3f}")
print()

# Step 5: Save model
print("💾 Step 5: Saving model...")

import joblib
from pathlib import Path

model_dir = Path("models/saved_models")
model_dir.mkdir(parents=True, exist_ok=True)

model_path = model_dir / "stock_model_v1.pkl"

model_data = {
    'model': model,
    'feature_names': feature_names,
    'trained_date': datetime.now(),
    'metrics': {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'roc_auc': roc_auc
    },
    'training_samples': len(X_train),
    'test_samples': len(X_test)
}

joblib.dump(model_data, model_path)

print(f"   ✅ Model saved to: {model_path}")
print()

print("=" * 80)
print("✅ TRAINING COMPLETE!")
print("=" * 80)
print()
print("Next step: Test your Discord bot")
print("  python bot_with_real_data.py")
print()

