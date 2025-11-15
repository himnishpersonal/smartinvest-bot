#!/usr/bin/env python3
"""
Verify SmartInvest Bot setup before launching
"""
import sys
import os

def check_environment():
    """Check Python environment"""
    print("🔍 Checking Python environment...")
    print(f"   Python version: {sys.version.split()[0]}")
    
    if sys.version_info < (3, 9):
        print("   ❌ Python 3.9+ required")
        return False
    print("   ✅ Python version OK")
    return True


def check_dependencies():
    """Check required packages"""
    print("\n🔍 Checking dependencies...")
    
    required = [
        'discord',
        'yfinance',
        'pandas',
        'numpy',
        'sqlalchemy',
        'transformers',
        'xgboost',
        'sklearn',
        'pytz'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} missing")
            missing.append(package)
    
    if missing:
        print(f"\n   Install missing: pip install {' '.join(missing)}")
        return False
    
    return True


def check_env_file():
    """Check .env configuration"""
    print("\n🔍 Checking configuration...")
    
    if not os.path.exists('.env'):
        print("   ❌ .env file not found")
        return False
    print("   ✅ .env file exists")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'DISCORD_BOT_TOKEN',
        'DISCORD_CHANNEL_ID',
        'DATABASE_URL'
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == f'your_{var.lower()}':
            print(f"   ❌ {var} not configured")
            missing.append(var)
        else:
            print(f"   ✅ {var} configured")
    
    # Optional
    if os.getenv('NEWS_API_KEY'):
        print("   ✅ NEWS_API_KEY configured (optional)")
    else:
        print("   ⚠️  NEWS_API_KEY not configured (optional)")
    
    return len(missing) == 0


def check_database():
    """Check database connection"""
    print("\n🔍 Checking database...")
    
    try:
        from data.database import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'stocks', 'stock_prices', 'fundamentals',
            'news_articles', 'recommendations',
            'user_watchlists', 'user_alerts'
        ]
        
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if missing_tables:
            print(f"   ❌ Missing tables: {', '.join(missing_tables)}")
            print("   Run: python -c 'from data.database import init_db; init_db()'")
            return False
        
        print(f"   ✅ All {len(tables)} tables exist")
        return True
        
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False


def check_bot_imports():
    """Check bot can be imported"""
    print("\n🔍 Checking bot module...")
    
    try:
        from bot import SmartInvestBot
        print("   ✅ Bot module imports successfully")
        return True
    except Exception as e:
        print(f"   ❌ Bot import error: {e}")
        return False


def main():
    """Run all checks"""
    print("=" * 60)
    print("SmartInvest Bot - Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Environment", check_environment),
        ("Dependencies", check_dependencies),
        ("Configuration", check_env_file),
        ("Database", check_database),
        ("Bot Module", check_bot_imports),
    ]
    
    results = {}
    for name, check_func in checks:
        results[name] = check_func()
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<40} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 Setup verification complete! Ready to launch!")
        print("\nTo start the bot, run:")
        print("   python bot.py")
        print("\nThen test in Discord:")
        print("   /help - See all commands")
        print("   /daily - View recommendations")
        print("   /stock AAPL - Analyze a stock")
        return 0
    else:
        print("\n⚠️  Some checks failed. Fix the issues above before launching.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

