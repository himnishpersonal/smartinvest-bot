#!/usr/bin/env python3
"""
Check if news and fundamentals are up to date.
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.storage import DatabaseManager
from config import Config

def main():
    db = DatabaseManager(Config.DATABASE_URL)
    
    print('=' * 60)
    print('📰 NEWS SENTIMENT CHECK')
    print('=' * 60)
    
    stock = db.get_stock_by_ticker('AAPL')
    if stock:
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Get recent news
        recent_news = db.get_news_articles(stock.id, limit=10)
        if recent_news:
            print(f'\nSample news for AAPL (latest 10):')
            today_count = 0
            yesterday_count = 0
            
            for news in recent_news:
                pub_date = news.published_at.date() if hasattr(news.published_at, 'date') else news.published_at
                age = (today - pub_date).days
                
                if pub_date == today:
                    status = '✅ TODAY'
                    today_count += 1
                elif pub_date == yesterday:
                    status = '⚠️  YESTERDAY'
                    yesterday_count += 1
                else:
                    status = f'📅 {age} days ago'
                
                print(f'  {pub_date} | {status} | {news.title[:45]}...')
            
            print(f'\n📊 Summary:')
            print(f'  Today: {today_count} articles')
            print(f'  Yesterday: {yesterday_count} articles')
            
            if today_count > 0:
                print(f'  ✅ News refresh is working!')
            else:
                print(f'  ⚠️  No articles from today yet')
        else:
            print('  ❌ No news articles found')
    
    print()
    print('=' * 60)
    print('📊 FUNDAMENTALS CHECK')
    print('=' * 60)
    
    # Check fundamentals for a few stocks
    stocks_to_check = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']
    found_count = 0
    
    for ticker in stocks_to_check:
        stock = db.get_stock_by_ticker(ticker)
        if stock:
            fundamentals = db.get_latest_fundamentals(stock.id)
            if fundamentals:
                # fundamentals is a Fundamental object, not a dict
                pe = fundamentals.pe_ratio if hasattr(fundamentals, 'pe_ratio') else None
                roe = fundamentals.roe if hasattr(fundamentals, 'roe') else None
                
                pe_str = f"{pe:.2f}" if isinstance(pe, (int, float)) and pe is not None else "N/A"
                roe_str = f"{roe:.2f}%" if isinstance(roe, (int, float)) and roe is not None else "N/A"
                print(f'  {ticker:6s} | P/E: {pe_str:>8s} | ROE: {roe_str:>8s} | ✅ Available')
                found_count += 1
            else:
                print(f'  {ticker:6s} | ❌ No fundamentals')
    
    print()
    if found_count > 0:
        print(f'✅ {found_count}/{len(stocks_to_check)} stocks have fundamentals')
    else:
        print('⚠️  No fundamentals found. May need to run refresh.')
    
    print('=' * 60)

if __name__ == '__main__':
    main()

