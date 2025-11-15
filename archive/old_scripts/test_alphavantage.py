"""
Test script to verify Alpha Vantage integration.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.collectors import StockDataCollector

def test_alpha_vantage():
    """Test Alpha Vantage API integration."""
    print("=" * 60)
    print("Testing Alpha Vantage Integration")
    print("=" * 60)
    
    # Check if API key is set
    api_key = os.getenv('VANTAGE_API_KEY')
    if not api_key:
        print("❌ VANTAGE_API_KEY not found in environment")
        print("   Please add it to your .env file")
        return False
    
    print(f"✓ API Key found: {api_key[:8]}...")
    print()
    
    # Initialize collector
    try:
        collector = StockDataCollector(api_key=api_key)
        print("✓ StockDataCollector initialized with Alpha Vantage")
    except Exception as e:
        print(f"❌ Failed to initialize collector: {e}")
        return False
    
    print()
    print("-" * 60)
    print("Test 1: Fetch Current Price")
    print("-" * 60)
    
    try:
        price_info = collector.fetch_current_price('AAPL')
        if price_info:
            print(f"✓ AAPL Price: ${price_info['price']:.2f}")
            print(f"  Change: {price_info['change']:+.2f} ({price_info['change_percent']:+.2f}%)")
            print(f"  Volume: {price_info['volume']:,}")
        else:
            print("❌ No price data returned")
            return False
    except Exception as e:
        print(f"❌ Error fetching current price: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("-" * 60)
    print("Test 2: Fetch Price History")
    print("-" * 60)
    
    try:
        df = collector.fetch_price_history('MSFT', period='1mo', interval='1d')
        if df is not None and not df.empty:
            print(f"✓ MSFT Price History: {len(df)} records")
            print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"  Latest close: ${df['close'].iloc[-1]:.2f}")
            print()
            print("  Sample data:")
            print(df.tail(3).to_string(index=False))
        else:
            print("❌ No price history returned")
            return False
    except Exception as e:
        print(f"❌ Error fetching price history: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("-" * 60)
    print("Test 3: Fetch Fundamentals")
    print("-" * 60)
    
    try:
        fundamentals = collector.fetch_fundamentals('GOOGL')
        if fundamentals:
            print(f"✓ GOOGL Fundamentals:")
            print(f"  Sector: {fundamentals.get('sector')}")
            print(f"  Industry: {fundamentals.get('industry')}")
            print(f"  P/E Ratio: {fundamentals.get('pe_ratio')}")
            print(f"  ROE: {fundamentals.get('roe')}")
            print(f"  Market Cap: ${fundamentals.get('market_cap'):,.0f}" if fundamentals.get('market_cap') else "  Market Cap: N/A")
        else:
            print("❌ No fundamental data returned")
            return False
    except Exception as e:
        print(f"❌ Error fetching fundamentals: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("-" * 60)
    print("Test 4: Fetch Company Info")
    print("-" * 60)
    
    try:
        info = collector.fetch_company_info('TSLA')
        if info:
            print(f"✓ TSLA Company Info:")
            print(f"  Name: {info.get('company_name')}")
            print(f"  Sector: {info.get('sector')}")
            print(f"  Industry: {info.get('industry')}")
            print(f"  Country: {info.get('country')}")
            print(f"  Exchange: {info.get('exchange')}")
        else:
            print("❌ No company info returned")
            return False
    except Exception as e:
        print(f"❌ Error fetching company info: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("=" * 60)
    print("✅ All tests passed! Alpha Vantage integration working!")
    print("=" * 60)
    print()
    print("NOTE: Alpha Vantage free tier has rate limits:")
    print("  - 5 API calls per minute")
    print("  - 25 API calls per day on free tier")
    print("  - The bot will automatically handle rate limiting")
    print()
    
    return True


if __name__ == '__main__':
    success = test_alpha_vantage()
    sys.exit(0 if success else 1)

