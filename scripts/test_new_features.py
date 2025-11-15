#!/usr/bin/env python3
"""
Comprehensive test script for new features:
- Performance Tracking
- Exit Signals
- Position Management
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.storage import DatabaseManager
from config import Config

def test_database_schema():
    """Test if new tables exist."""
    print("=" * 70)
    print("🔍 DATABASE SCHEMA CHECK")
    print("=" * 70)
    
    db = DatabaseManager(Config.DATABASE_URL)
    
    # Check if tables exist by trying to query them
    try:
        positions = db.get_all_open_positions()
        print(f"✅ user_positions table exists | {len(positions)} open positions")
    except Exception as e:
        print(f"❌ user_positions table error: {e}")
    
    try:
        signals = db.get_active_exit_signals()
        print(f"✅ exit_signals table exists | {len(signals)} active signals")
    except Exception as e:
        print(f"❌ exit_signals table error: {e}")
    
    try:
        trackers = db.get_active_performance_trackers()
        print(f"✅ recommendation_performance table exists | {len(trackers)} active trackers")
    except Exception as e:
        print(f"❌ recommendation_performance table error: {e}")
    
    print()

def test_position_management():
    """Test position CRUD operations."""
    print("=" * 70)
    print("🎯 POSITION MANAGEMENT TEST")
    print("=" * 70)
    
    db = DatabaseManager(Config.DATABASE_URL)
    
    # Check existing positions
    positions = db.get_user_positions("test_user_123")
    print(f"📊 Test user has {len(positions)} positions")
    
    for pos in positions:
        print(f"  • {pos.stock.ticker if pos.stock else 'Unknown'}: {pos.shares} shares @ ${pos.entry_price:.2f} ({pos.status})")
    
    print()

def test_exit_signals():
    """Test exit signal detection."""
    print("=" * 70)
    print("🚨 EXIT SIGNALS TEST")
    print("=" * 70)
    
    db = DatabaseManager(Config.DATABASE_URL)
    
    # Get all active signals
    signals = db.get_active_exit_signals()
    print(f"📊 Total active exit signals: {len(signals)}")
    
    if signals:
        print("\nRecent signals:")
        for signal, position, stock in signals[:5]:
            urgency_emoji = "🔴" if signal.urgency == "high" else "🟡" if signal.urgency == "medium" else "🟢"
            print(f"  {urgency_emoji} {stock.ticker}: {signal.signal_type} | {signal.reason[:50]}...")
    else:
        print("  ℹ️  No active exit signals (this is normal if no positions are tracked)")
    
    print()

def test_performance_tracking():
    """Test performance tracking."""
    print("=" * 70)
    print("📈 PERFORMANCE TRACKING TEST")
    print("=" * 70)
    
    db = DatabaseManager(Config.DATABASE_URL)
    
    # Get active trackers
    trackers = db.get_active_performance_trackers()
    print(f"📊 Active performance trackers: {len(trackers)}")
    
    if trackers:
        print("\nRecent trackers:")
        for tracker in trackers[:5]:
            rec = tracker.recommendation
            stock = rec.stock if rec else None
            ticker = stock.ticker if stock else "Unknown"
            
            return_5d = tracker.return_5d or 0
            status_emoji = "✅" if return_5d > 0 else "❌" if return_5d < 0 else "⚪"
            
            print(f"  {status_emoji} {ticker}: Entry ${tracker.entry_price:.2f} | 5d: {return_5d:+.2f}% | Status: {tracker.status}")
    else:
        print("  ℹ️  No performance trackers yet")
        print("  💡 Generate recommendations with /daily to start tracking")
    
    # Get performance stats
    stats = db.get_performance_stats(days=30)
    if stats and stats.get('total_recommendations', 0) > 0:
        print(f"\n📊 30-Day Performance Summary:")
        print(f"  Total Recommendations: {stats['total_recommendations']}")
        if '5day' in stats:
            print(f"  5-Day Win Rate: {stats['5day']['win_rate']:.1f}%")
            print(f"  5-Day Avg Return: {stats['5day']['avg_return']:+.2f}%")
    
    print()

def test_daily_refresh_integration():
    """Check if daily refresh scripts are set up correctly."""
    print("=" * 70)
    print("⏰ DAILY REFRESH INTEGRATION")
    print("=" * 70)
    
    # Check if the monitoring scripts exist
    scripts_dir = Path(__file__).parent
    
    scripts_to_check = [
        ('update_performance.py', 'Updates recommendation performance daily'),
        ('monitor_exit_signals.py', 'Checks for exit signals on open positions'),
        ('daily_refresh.py', 'Main daily refresh script')
    ]
    
    for script_name, description in scripts_to_check:
        script_path = scripts_dir / script_name
        if script_path.exists():
            print(f"  ✅ {script_name:<25s} - {description}")
        else:
            print(f"  ❌ {script_name:<25s} - MISSING")
    
    print()

def test_discord_commands():
    """List Discord commands to test manually."""
    print("=" * 70)
    print("🤖 DISCORD BOT COMMANDS TO TEST")
    print("=" * 70)
    
    commands = [
        ("Position Management", [
            "/position add ticker:AAPL shares:10 entry_price:180",
            "/position close ticker:AAPL exit_price:185",
            "/positions",
            "/track"
        ]),
        ("Exit Signals", [
            "/exits"
        ]),
        ("Performance Tracking", [
            "/performance days:30 strategy:all",
            "/leaderboard limit:10 timeframe:5day"
        ]),
        ("Generate Data", [
            "/daily (to generate new tracked recommendations)"
        ])
    ]
    
    for category, cmds in commands:
        print(f"\n📋 {category}:")
        for cmd in cmds:
            print(f"  • {cmd}")
    
    print()

def main():
    print("\n")
    print("=" * 70)
    print("🧪 SMARTINVEST NEW FEATURES TEST SUITE")
    print("=" * 70)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        test_database_schema()
        test_position_management()
        test_exit_signals()
        test_performance_tracking()
        test_daily_refresh_integration()
        test_discord_commands()
        
        print("=" * 70)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 70)
        print()
        print("📝 NEXT STEPS:")
        print("  1. Test Discord commands listed above")
        print("  2. Generate new recommendations with /daily")
        print("  3. Add a test position with /position add")
        print("  4. Wait 24 hours for automated monitoring to run")
        print("  5. Check /performance and /exits tomorrow")
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

