"""
Test script for backtesting functionality
Run this to verify backtesting works before using Discord command
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from config import Config
from data.storage import DatabaseManager
from models.backtester import Backtester, PortfolioSimulator
from utils.performance import PerformanceAnalyzer
from utils.visualizer import BacktestVisualizer

# Import bot's feature calculator to ensure consistency
from bot_with_real_data import SmartInvestBot

# Initialize bot to get feature calculator
_bot_instance = None

def get_feature_calculator():
    """Get the bot's feature calculation function."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = SmartInvestBot()
    return _bot_instance._calculate_backtest_features


def main():
    """
    Run a simple backtest to verify everything works.
    """
    print("\n" + "="*60)
    print("SMARTINVEST BACKTESTING TEST")
    print("="*60 + "\n")
    
    # Initialize database
    print("1. Connecting to database...")
    db_manager = DatabaseManager(Config.DATABASE_URL)
    
    # Check stocks
    stocks = db_manager.get_all_stocks()
    print(f"   ✓ Found {len(stocks)} stocks in database")
    
    if len(stocks) < 10:
        print("\n❌ ERROR: Need at least 10 stocks for backtesting")
        print("   Run: python scripts/load_full_sp500.py")
        return
    
    # Load ML model (optional)
    print("\n2. Loading ML model...")
    try:
        import joblib
        model_path = 'models/saved_models/model_latest.pkl'
        if os.path.exists(model_path):
            ml_model_dict = joblib.load(model_path)
            # Extract model from dict if needed (matches bot structure)
            ml_model = ml_model_dict.get('model') if isinstance(ml_model_dict, dict) else ml_model_dict
            print(f"   ✓ ML model loaded from {model_path}")
        else:
            ml_model = None
            print("   ⚠  No ML model found - using rule-based scoring")
    except Exception as e:
        ml_model = None
        print(f"   ⚠  Could not load ML model: {e}")
    
    # Set backtest parameters
    print("\n3. Setting up backtest...")
    start_date = date(2025, 10, 1)  # Start October 1 (more historical data available)
    end_date = date(2025, 10, 31)  # End October 31 (1 month period)
    capital = 10000
    hold_days = 5
    
    print(f"   Period: {start_date} to {end_date}")
    print(f"   Starting capital: ${capital:,}")
    print(f"   Hold period: {hold_days} days")
    
    # Initialize backtester with bot's feature calculator
    print("\n4. Initializing backtester...")
    feature_calculator = get_feature_calculator()
    backtester = Backtester(
        db_manager=db_manager,
        ml_model=ml_model,
        feature_calculator=feature_calculator
    )
    print("   ✓ Backtester ready")
    
    # Initialize simulator
    print("\n5. Initializing portfolio simulator...")
    simulator = PortfolioSimulator(
        starting_capital=capital,
        hold_days=hold_days,
        max_positions=10
    )
    print("   ✓ Simulator ready")
    
    # Run backtest
    print("\n6. Running backtest...")
    print("   This may take 30-60 seconds...\n")
    
    try:
        results = simulator.run_backtest(backtester, start_date, end_date)
        print(f"\n   ✓ Backtest complete!")
        print(f"   Total trades executed: {len(results['closed_trades'])}")
        
    except Exception as e:
        print(f"\n   ❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Calculate metrics
    print("\n7. Calculating performance metrics...")
    analyzer = PerformanceAnalyzer(
        closed_trades=results['closed_trades'],
        equity_curve=results['equity_curve'],
        starting_capital=capital
    )
    metrics = analyzer.calculate_all_metrics()
    print("   ✓ Metrics calculated")
    
    # Display results
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    
    print(f"\n💰 Returns:")
    print(f"   Starting Capital:  ${metrics['starting_capital']:,.0f}")
    print(f"   Ending Value:      ${metrics['final_value']:,.0f}")
    print(f"   Total Return:      {metrics['total_return_pct']:+.2f}%")
    print(f"   S&P 500 Return:    {metrics['benchmark_return']:+.2f}%")
    print(f"   Alpha:             {metrics['alpha']:+.2f}%")
    
    print(f"\n📈 Trade Statistics:")
    print(f"   Total Trades:      {metrics['total_trades']}")
    print(f"   Winners:           {metrics['winning_trades']} ({metrics['win_rate']:.1f}%)")
    print(f"   Losers:            {metrics['losing_trades']}")
    print(f"   Avg Win:           +{metrics['avg_win']:.2f}%")
    print(f"   Avg Loss:          {metrics['avg_loss']:.2f}%")
    print(f"   Avg Hold Period:   {metrics['avg_days_held']:.1f} days")
    
    print(f"\n⚠️  Risk Metrics:")
    print(f"   Sharpe Ratio:      {metrics['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown:      {metrics['max_drawdown']:.2f}%")
    print(f"   Profit Factor:     {metrics['profit_factor']:.2f}")
    
    if metrics['best_trade']:
        best = metrics['best_trade']
        print(f"\n🏆 Best Trade:")
        print(f"   {best['ticker']}: {best['pnl_pct']:+.2f}%")
        print(f"   {best['entry_date']} → {best['exit_date']}")
    
    if metrics['worst_trade']:
        worst = metrics['worst_trade']
        print(f"\n💀 Worst Trade:")
        print(f"   {worst['ticker']}: {worst['pnl_pct']:+.2f}%")
        print(f"   {worst['entry_date']} → {worst['exit_date']}")
    
    # Generate charts
    print("\n8. Generating visualizations...")
    visualizer = BacktestVisualizer()
    
    try:
        equity_chart = visualizer.plot_equity_curve(results['equity_curve'])
        print(f"   ✓ Equity curve: {equity_chart}")
        
        drawdown_chart = visualizer.plot_drawdown(results['equity_curve'])
        print(f"   ✓ Drawdown chart: {drawdown_chart}")
        
        trade_dist = visualizer.plot_trade_distribution(results['closed_trades'])
        print(f"   ✓ Trade distribution: {trade_dist}")
        
    except Exception as e:
        print(f"   ⚠  Chart generation error: {e}")
    
    # Summary
    print("\n" + "="*60)
    if metrics['total_return_pct'] > 10:
        print("✅ EXCELLENT! System showed strong performance.")
    elif metrics['total_return_pct'] > 0:
        print("✅ GOOD! System was profitable.")
    else:
        print("⚠️  System needs improvement for this period.")
    
    print("\n📊 Backtesting system is working correctly!")
    print("   You can now use /backtest command in Discord")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

