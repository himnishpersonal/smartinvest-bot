"""
Demo script showing DataPipeline usage
"""

import os
from data import (
    DatabaseManager, 
    StockDataCollector, 
    NewsCollector, 
    SentimentAnalyzer,
    DataPipeline
)


def demo():
    """Demonstrate DataPipeline functionality."""
    print("=" * 60)
    print("SmartInvest Data Pipeline Demo")
    print("=" * 60)
    
    # Initialize components
    print("\n1️⃣ Initializing components...")
    
    # Database
    db_manager = DatabaseManager('sqlite:///demo.db')
    
    # Collectors
    stock_collector = StockDataCollector()
    
    # News collector (requires API key)
    api_key = os.getenv('NEWS_API_KEY')
    if api_key:
        news_collector = NewsCollector(api_key)
    else:
        print("⚠️  NEWS_API_KEY not set - news collection will be skipped")
        news_collector = None
    
    # Sentiment analyzer
    print("   Loading FinBERT model... (this may take a minute on first run)")
    sentiment_analyzer = SentimentAnalyzer()
    
    # Initialize pipeline
    if news_collector:
        pipeline = DataPipeline(db_manager, stock_collector, news_collector, sentiment_analyzer)
    else:
        print("   ⚠️  Pipeline initialized without news collector")
    
    print("   ✅ All components initialized")
    
    # Small test with just a few stocks
    test_tickers = ['AAPL', 'MSFT', 'GOOGL']
    
    print(f"\n2️⃣ Testing with {len(test_tickers)} stocks: {', '.join(test_tickers)}")
    
    # Update stock universe
    print("\n   Updating stock universe...")
    try:
        valid_tickers = pipeline.update_stock_universe(config_stock_universe=test_tickers, 
                                                       min_price=1.0, min_volume=100000)
        print(f"   ✅ {len(valid_tickers)} stocks in universe")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Update fundamentals
    print("\n   Updating fundamentals...")
    try:
        fundamentals = pipeline.update_fundamental_data(valid_tickers)
        print(f"   ✅ Fundamentals updated for {sum(1 for v in fundamentals.values() if v)} stocks")
        
        # Show sample
        for ticker, fund in list(fundamentals.items())[:2]:
            if fund:
                print(f"      {ticker}: P/E={fund.get('pe_ratio', 'N/A')}, ROE={fund.get('roe', 'N/A'):.2%}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    db_manager.close()
    print("   ✅ Demo complete")
    
    print("\n" + "=" * 60)
    print("Note: Full pipeline with news & sentiment requires NEWS_API_KEY")
    print("      This demo ran without news collection")
    print("=" * 60)


if __name__ == '__main__':
    demo()
