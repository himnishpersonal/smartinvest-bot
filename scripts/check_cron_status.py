#!/usr/bin/env python3
"""
Quick script to check if the daily refresh cron job ran successfully.
"""

import sys
import os
from datetime import date, datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from data.storage import DatabaseManager

def check_cron_status():
    """Check if cron job ran by examining database timestamps."""
    
    print("=" * 60)
    print("🔍 CRON JOB STATUS CHECK")
    print("=" * 60)
    print()
    
    # Initialize database
    db = DatabaseManager(Config.DATABASE_URL)
    
    # Get all stocks
    stocks = db.get_all_stocks()
    print(f"📊 Total stocks in database: {len(stocks)}")
    print()
    
    # Check latest price dates for sample stocks
    print("📅 Checking latest price dates (sample of 10 stocks):")
    print("-" * 60)
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    recent_count = 0
    old_count = 0
    
    for stock in stocks[:10]:
        latest_price = db.get_latest_price(stock.id)
        if latest_price:
            price_date = latest_price.date.date() if hasattr(latest_price.date, 'date') else latest_price.date
            
            if price_date == today:
                status = "✅ TODAY"
                recent_count += 1
            elif price_date == yesterday:
                status = "⚠️  YESTERDAY"
            else:
                status = f"❌ {price_date.strftime('%Y-%m-%d')}"
                old_count += 1
            
            print(f"  {stock.ticker:6s} | Latest: {price_date} | {status}")
        else:
            print(f"  {stock.ticker:6s} | No price data")
    
    print()
    print("-" * 60)
    
    # Check if log file exists
    log_path = Path(__file__).parent.parent / "logs" / "daily_refresh.log"
    print(f"📝 Log file: {log_path}")
    
    if log_path.exists():
        # Get last modified time
        mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
        age = datetime.now() - mtime
        
        if age < timedelta(hours=24):
            print(f"   ✅ Last updated: {mtime.strftime('%Y-%m-%d %H:%M:%S')} ({age.seconds // 3600}h ago)")
            
            # Show last few lines
            print()
            print("   Last 5 lines of log:")
            with open(log_path, 'r') as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    print(f"   {line.rstrip()}")
        else:
            print(f"   ⚠️  Last updated: {mtime.strftime('%Y-%m-%d %H:%M:%S')} ({age.days} days ago)")
    else:
        print("   ❌ Log file does not exist")
    
    print()
    print("-" * 60)
    
    # Check crontab
    print("⏰ Checking crontab schedule:")
    import subprocess
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if 'daily_refresh' in result.stdout:
            print("   ✅ Cron job found in crontab")
            for line in result.stdout.split('\n'):
                if 'daily_refresh' in line:
                    print(f"   {line.strip()}")
        else:
            print("   ❌ No daily_refresh found in crontab")
    except:
        print("   ⚠️  Could not read crontab")
    
    print()
    print("=" * 60)
    
    # Summary
    if recent_count > 0:
        print("✅ CONCLUSION: Cron job appears to have run recently!")
    elif old_count > 0:
        print("⚠️  CONCLUSION: Data is older than today. Cron may not have run.")
    else:
        print("❓ CONCLUSION: Unable to determine. Check logs manually.")
    
    print("=" * 60)

if __name__ == "__main__":
    check_cron_status()

