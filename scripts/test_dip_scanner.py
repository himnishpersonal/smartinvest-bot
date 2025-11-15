"""
Test script for the dip scanner functionality.
Tests the buy-the-dip feature independently of Discord.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from data.storage import DatabaseManager
from models.dip_scanner import DipScanner
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test the dip scanner"""
    print("\n" + "="*70)
    print("BUY THE DIP SCANNER - TEST")
    print("="*70 + "\n")
    
    # Initialize components
    logger.info("Initializing database and dip scanner...")
    db_manager = DatabaseManager(Config.DATABASE_URL)
    dip_scanner = DipScanner(db_manager=db_manager, min_dip_score=60)
    
    # Get stock count
    stocks = db_manager.get_all_stocks()
    logger.info(f"Database has {len(stocks)} stocks")
    
    # Find dip candidates
    print("\n🔍 Scanning for dip opportunities...")
    print("Looking for: Stocks down 10-30%, RSI < 40, strong fundamentals (yfinance)\n")
    
    candidates = dip_scanner.find_dip_candidates(limit=10)
    
    if not candidates:
        print("❌ No dip opportunities found.")
        print("\nPossible reasons:")
        print("  • Market is strong (no significant drops)")
        print("  • Stocks that dropped don't meet quality filters")
        print("  • Try lowering min_dip_score threshold")
        return
    
    # Display results
    print(f"\n✅ Found {len(candidates)} dip candidates!\n")
    print("="*70)
    
    for i, candidate in enumerate(candidates, 1):
        # Rank emoji
        if i == 1:
            emoji = "🥇"
        elif i == 2:
            emoji = "🥈"
        elif i == 3:
            emoji = "🥉"
        else:
            emoji = f"{i}."
        
        # RSI indicator
        rsi = candidate['rsi']
        if rsi < 30:
            rsi_indicator = "🔴 (Deeply Oversold)"
        elif rsi < 40:
            rsi_indicator = "🟡 (Oversold)"
        else:
            rsi_indicator = "🟢 (Weak)"
        
        # Get reason
        reason = dip_scanner.get_dip_reason(candidate)
        
        # Print candidate
        print(f"\n{emoji} {candidate['ticker']} - {candidate['company_name']}")
        print(f"   Sector: {candidate.get('sector', 'N/A')}")
        print(f"   Current Price: ${candidate['current_price']:.2f}")
        print(f"   Recent High: ${candidate['recent_high']:.2f}")
        print(f"   Drop: {candidate['price_drop_pct']:.1f}%")
        print(f"   5-day drop: {candidate['drop_5d_pct']:.1f}%")
        print(f"   10-day drop: {candidate['drop_10d_pct']:.1f}%")
        print(f"   RSI: {rsi:.0f} {rsi_indicator}")
        print(f"   Volume Ratio: {candidate['volume_ratio']:.2f}x")
        print(f"   Quality: {candidate['quality']}")
        print(f"   Risk Level: {candidate['risk_level']}")
        print(f"   Dip Score: {candidate['total_score']}/100")
        print(f"   Why: {reason}")
        print(f"   ")
        print(f"   Score Breakdown:")
        print(f"      - Price Drop: {candidate['price_score']}/30")
        print(f"      - RSI Oversold: {candidate['rsi_score']}/25")
        print(f"      - Volume Spike: {candidate['volume_score']}/15")
        print(f"      - Fundamentals: {candidate.get('fundamental_score', 0)}/30")
        
        # Display fundamental details if available
        if candidate.get('pe_ratio'):
            print(f"   ")
            print(f"   Fundamentals (yfinance):")
            if candidate.get('pe_ratio'):
                print(f"      - P/E Ratio: {candidate['pe_ratio']:.1f} ({candidate.get('pe_rating', 'N/A')})")
            if candidate.get('roe'):
                print(f"      - ROE: {candidate['roe']:.1f}% ({candidate.get('roe_rating', 'N/A')})")
            if candidate.get('debt_to_equity') is not None:
                print(f"      - Debt/Equity: {candidate['debt_to_equity']:.1f} ({candidate.get('debt_rating', 'N/A')})")
            if candidate.get('profit_margin'):
                print(f"      - Profit Margin: {candidate['profit_margin']:.1f}% ({candidate.get('margin_rating', 'N/A')})")
            if candidate.get('growth_rate'):
                print(f"      - Growth Rate: {candidate['growth_rate']:.1f}% ({candidate.get('growth_rating', 'N/A')})")
        
        print("-" * 70)
    
    # Summary statistics
    print(f"\n📊 SUMMARY")
    print("="*70)
    print(f"Total candidates found: {len(candidates)}")
    print(f"Average dip score: {sum(c['total_score'] for c in candidates) / len(candidates):.1f}")
    print(f"Average drop: {sum(c['price_drop_pct'] for c in candidates) / len(candidates):.1f}%")
    print(f"Average RSI: {sum(c['rsi'] for c in candidates) / len(candidates):.1f}")
    
    # Risk distribution
    risk_counts = {}
    for c in candidates:
        risk = c['risk_level']
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
    
    print(f"\nRisk Distribution:")
    for risk, count in sorted(risk_counts.items()):
        print(f"  {risk}: {count} stocks")
    
    print("\n" + "="*70)
    print("✅ Dip scanner test complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

