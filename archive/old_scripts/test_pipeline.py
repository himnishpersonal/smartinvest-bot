#!/usr/bin/env python3
"""
Manual test script for data pipeline
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from config import Config
from data.storage import DatabaseManager
from data.collectors import StockDataCollector, NewsCollector, SentimentAnalyzer
from data.pipeline import DataPipeline
from models.scoring import RecommendationEngine


def test_data_collection():
    """Test data collection components"""
    print("Testing data collection...")
    
    collector = StockDataCollector()
    
    # Test single ticker
    print("\n1. Fetching AAPL price data...")
    df = collector.fetch_price_history('AAPL', period='1mo')
    print(f"   ✓ Got {len(df)} days of data")
    
    # Test fundamentals
    print("\n2. Fetching AAPL fundamentals...")
    fundamentals = collector.fetch_fundamentals('AAPL')
    print(f"   ✓ Got fundamentals for AAPL")
    print(f"   P/E Ratio: {fundamentals.get('pe_ratio', 'N/A')}")
    
    return True


def test_news_and_sentiment():
    """Test news collection and sentiment analysis"""
    print("\nTesting news and sentiment...")
    
    config = Config()
    news_collector = NewsCollector(config.NEWS_API_KEY)
    sentiment_analyzer = SentimentAnalyzer()
    
    # Test news fetch
    print("\n1. Fetching AAPL news...")
    try:
        articles = news_collector.fetch_stock_news('AAPL', 'Apple Inc', days_back=3)
        print(f"   ✓ Found {len(articles)} articles")
        
        if articles:
            # Test sentiment analysis
            print("\n2. Analyzing sentiment...")
            article = articles[0]
            sentiment = sentiment_analyzer.analyze_text(article['title'])
            print(f"   ✓ Sentiment: {sentiment['sentiment_label']} ({sentiment['sentiment_score']:.2f})")
    except Exception as e:
        print(f"   ⚠️  News API not configured: {e}")
    
    return True


def test_recommendation_engine():
    """Test recommendation generation"""
    print("\nTesting recommendation engine...")
    
    config = Config()
    db_manager = DatabaseManager(config.DATABASE_URL)
    
    # This assumes model is trained
    try:
        rec_engine = RecommendationEngine(
            ml_model_path='models/saved_models/model_v1.pkl',
            feature_pipeline=None,
            db_manager=db_manager
        )
        
        print("\n1. Scoring AAPL...")
        score = rec_engine.score_single_stock('AAPL')
        print(f"   ✓ Score: {score['overall_score']}/100")
        print(f"   Top signal: {score['signals'][0]}")
        
        return True
    except FileNotFoundError:
        print("   ⚠️  Model not found. Train model first.")
        return False
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        return False


def main():
    """Run all manual tests"""
    print("=" * 60)
    print("SmartInvest Bot - Manual Test Suite")
    print("=" * 60)
    
    tests = [
        ("Data Collection", test_data_collection),
        ("News & Sentiment", test_news_and_sentiment),
        ("Recommendation Engine", test_recommendation_engine),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_name}")
        print('=' * 60)
        
        try:
            success = test_func()
            results[test_name] = "✅ PASSED" if success else "⚠️  PARTIAL"
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = "❌ FAILED"
    
    # Summary
    print(f"\n{'=' * 60}")
    print("Test Summary")
    print('=' * 60)
    for test_name, result in results.items():
        print(f"{test_name:.<40} {result}")
    print('=' * 60)


if __name__ == "__main__":
    main()
