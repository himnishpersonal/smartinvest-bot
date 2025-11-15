#!/usr/bin/env python3
"""
Fetch news and analyze sentiment for stocks in database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from datetime import datetime
from config import Config
from data.storage import DatabaseManager
from data.collectors import NewsCollector, SentimentAnalyzer

def fetch_news_for_stocks(db_manager, news_collector, sentiment_analyzer, max_stocks=None):
    """
    Fetch news and sentiment for stocks in database
    
    Args:
        db_manager: DatabaseManager instance
        news_collector: NewsCollector instance
        sentiment_analyzer: SentimentAnalyzer instance
        max_stocks: Maximum number of stocks to process (respects API limits)
    """
    print("=" * 80)
    print("SmartInvest Bot - News & Sentiment Fetcher")
    print("=" * 80)
    print()
    
    # Get stocks from database
    print("📊 Loading stocks from database...")
    stocks = db_manager.get_all_stocks()
    print(f"   Found {len(stocks)} stocks\n")
    
    if len(stocks) == 0:
        print("❌ No stocks in database. Run load_test_data.py first.")
        return
    
    # Limit to max_stocks if specified
    if max_stocks and len(stocks) > max_stocks:
        print(f"   Limiting to first {max_stocks} stocks")
        stocks = stocks[:max_stocks]
    
    # Warning about API limits
    print(f"📰 NewsAPI free tier: 500 requests/day")
    print(f"   Processing {len(stocks)} stocks")
    print(f"   Estimated API calls: ~{len(stocks)} (well under limit)")
    
    # Estimate time
    estimated_time = len(stocks) * 15  # ~15 seconds per stock (fetch + sentiment)
    print(f"   Estimated time: ~{estimated_time // 60} minutes {estimated_time % 60} seconds")
    
    response = input("\n   Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("   Cancelled.")
        return
    
    print(f"\n📰 Fetching news and analyzing sentiment...\n")
    
    successful = 0
    failed = 0
    no_articles = 0
    total_articles = 0
    start_time = time.time()
    
    for i, stock in enumerate(stocks, 1):
        try:
            # Progress indicator with time estimate
            elapsed = time.time() - start_time
            if i > 1:
                avg_time = elapsed / (i - 1)
                remaining = avg_time * (len(stocks) - i + 1)
                print(f"[{i}/{len(stocks)}] {stock.ticker} - {stock.company_name[:30]} (ETA: {int(remaining//60)}m {int(remaining%60)}s)", end=" ")
            else:
                print(f"[{i}/{len(stocks)}] {stock.ticker} - {stock.company_name[:30]}", end=" ")
            
            # Fetch news
            articles = news_collector.fetch_stock_news(
                stock.ticker,
                stock.company_name,
                days_back=7
            )
            
            if not articles:
                print("(no articles)")
                no_articles += 1
                continue
            
            print(f"({len(articles)} articles)", end=" ")
            total_articles += len(articles)
            
            # Analyze sentiment for each article
            for article in articles:
                try:
                    # Analyze sentiment
                    sentiment = sentiment_analyzer.analyze_text(article['title'])
                    
                    # Store in database
                    db_manager.add_news_article(
                        stock_id=stock.id,
                        title=article['title'],
                        source=article['source'],
                        url=article['url'],
                        published_at=article['published_at'],
                        sentiment_score=sentiment['sentiment_score'],
                        sentiment_label=sentiment['sentiment_label']
                    )
                except Exception as e:
                    print(f"\n      ⚠️  Sentiment analysis failed: {str(e)[:50]}")
            
            print("✓")
            successful += 1
            
            # Small delay to be nice to APIs
            time.sleep(0.5)
            
        except Exception as e:
            print(f"✗ Error: {str(e)[:50]}")
            failed += 1
    
    # Summary
    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"✅ Successful: {successful} stocks")
    print(f"📰 Total articles: {total_articles} articles")
    print(f"📊 No articles: {no_articles} stocks")
    print(f"❌ Failed: {failed} stocks")
    print(f"⏱️  Total time: {int(total_time//60)}m {int(total_time%60)}s")
    print("\n✅ News & sentiment collection complete!")
    print("\nNext step:")
    print("   Run: python scripts/train_model.py")
    print("   (Model will now include sentiment features)")
    print("=" * 80)


def main():
    """Main function"""
    config = Config()
    db_manager = DatabaseManager(config.DATABASE_URL)
    
    # Check if NewsAPI key is configured
    if not config.NEWS_API_KEY or config.NEWS_API_KEY == 'your_newsapi_key':
        print("⚠️  NewsAPI key not configured in .env")
        print("   News fetching will be skipped.")
        print("   You can still proceed with training using price data only.")
        response = input("\n   Skip news and continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            return
        # Continue without news
        print("\n✅ Continuing without news data...")
        return
    
    news_collector = NewsCollector(config.NEWS_API_KEY)
    sentiment_analyzer = SentimentAnalyzer()
    
    # Fetch news for all stocks (no limit)
    fetch_news_for_stocks(db_manager, news_collector, sentiment_analyzer)


if __name__ == "__main__":
    main()

