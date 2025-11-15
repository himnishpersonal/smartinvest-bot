# New Backtest Commands - Implementation Guide

**Date:** November 13, 2025  
**Status:** ✅ Complete

---

## 🎯 New Features

Added **two new backtesting commands** to the Discord bot:

1. **`/backtest-dip`** - Test the dip-buying strategy
2. **`/backtest-stock`** - Test individual stock performance

---

## 📋 Commands Overview

### 1. `/backtest-dip` - Dip Strategy Backtest

**Purpose:** Validate the "buy the dip" strategy with historical data

**Usage:**
```
/backtest-dip
/backtest-dip days:90 capital:10000 hold_days:15 max_positions:5
```

**Parameters:**
- `days` (optional): Number of days to backtest (30-365, default: 90)
- `capital` (optional): Starting capital ($1,000-$1,000,000, default: $10,000)
- `hold_days` (optional): Days to hold each position (5-60, default: 15)
- `max_positions` (optional): Max concurrent positions (1-10, default: 5)

**What It Does:**
1. Scans for dip candidates each day (using historical data)
2. Buys top-scoring dips (up to `max_positions`)
3. Holds for `hold_days` days
4. Tracks wins, losses, returns
5. Shows comprehensive results

**Example Output:**
```
📉 Dip Strategy Backtest Results (90 Days)

💰 Returns
Starting: $10,000
Ending: $11,250
Total Return: 🟢 +12.50%

📈 Trade Statistics
Total Trades: 28
Winners: 18 (64.3%)
Losers: 10
Avg Win: +8.50%
Avg Loss: -3.20%
Avg Hold: 15.2 days

🏆 Best Trade
NVDA: +24.75%
(2025-09-15 → 2025-09-30)

💀 Worst Trade
META: -8.17%
(2025-10-01 → 2025-10-16)

📝 Interpretation
✅ Strong performance. Dip strategy showed positive edge.
```

---

### 2. `/backtest-stock` - Individual Stock Backtest

**Purpose:** Test buy-and-hold performance for a specific stock

**Usage:**
```
/backtest-stock AAPL
/backtest-stock TSLA days:180 capital:5000
```

**Parameters:**
- `ticker` (required): Stock ticker symbol (e.g., AAPL, MSFT)
- `days` (optional): Number of days to backtest (30-365, default: 90)
- `capital` (optional): Starting capital ($100-$1,000,000, default: $10,000)

**What It Does:**
1. Buys stock at start date
2. Holds until end date
3. Calculates returns, volatility, drawdown
4. Shows news sentiment during period
5. Provides performance summary

**Example Output:**
```
📊 AAPL Backtest Results (90 Days)
Apple Inc. - Buy & Hold Strategy

💰 Performance
Entry Price: $175.50
Exit Price: $192.30
Total Return: 🟢 +9.57%
Profit: 🟢 +$957.00

📈 Position
Capital: $10,000
Shares: 56
Entry Value: $9,828.00
Exit Value: $10,768.80

⚠️ Risk
Volatility: 18.5%
Max Drawdown: -5.2%
Days Held: 90

📰 News Sentiment
Avg Sentiment: 😊 0.215
Articles: 47

📝 Summary
✅ Strong performer! Annualized: ~42.3%
```

---

## 🔧 Technical Implementation

### Files Created

**1. `models/dip_backtester.py`**
- `DipBacktester` class: Tests dip-buying strategy
- `StockBacktester` class: Tests individual stock performance
- Prevents lookahead bias (only uses past data)
- Simulates realistic trading (position sizing, hold periods)

**2. Discord Commands**
- Added to `bot_with_real_data.py`
- Rich embed formatting
- Input validation
- Error handling

---

## 🎯 Use Cases

### Dip Strategy Backtest

**When to use:**
- Before deploying dip strategy with real money
- To optimize hold_days parameter
- To compare dip vs. momentum strategies
- Monthly validation of strategy performance

**Key Metrics to Watch:**
- Win rate > 60% (dips should bounce)
- Avg win / Avg loss ratio > 2:1 (asymmetric payoff)
- Total return > S&P 500 benchmark

**Optimization:**
```bash
# Test different hold periods
/backtest-dip hold_days:10  # Short-term bounces
/backtest-dip hold_days:20  # Medium-term recovery
/backtest-dip hold_days:30  # Long-term reversion

# Test position concentration
/backtest-dip max_positions:3  # Concentrated (higher risk)
/backtest-dip max_positions:8  # Diversified (lower risk)
```

---

### Individual Stock Backtest

**When to use:**
- Considering buying a specific stock
- Compare stock vs. portfolio strategy
- Analyze stock volatility/risk
- Understand historical performance

**Example Workflow:**
```bash
# 1. See stock recommendation
/stock NVDA

# 2. Check historical performance
/backtest-stock NVDA days:90

# 3. Compare to longer period
/backtest-stock NVDA days:180

# 4. Compare to competitors
/backtest-stock AMD days:90
/backtest-stock INTC days:90

# 5. Make informed decision based on data
```

---

## 📊 Strategy Comparison Matrix

| Strategy          | Command              | Win Rate | Hold Period | Best For                    |
|-------------------|----------------------|----------|-------------|-----------------------------|
| Momentum          | `/backtest`          | ~48%     | 5-7 days    | Trending markets            |
| Dip Buying        | `/backtest-dip`      | ~60%     | 15-20 days  | Volatile/oversold markets   |
| Buy & Hold (Stock)| `/backtest-stock`    | N/A      | Any         | Individual stock analysis   |

---

## 🚀 Next Steps After Backtesting

### If Dip Strategy Performs Well (>10% return, >55% win rate)

1. **Start Small:** Deploy with 10-20% of capital
2. **Monitor Live:** Track actual vs. backtest performance
3. **Adjust Parameters:** Optimize based on live results
4. **Scale Gradually:** Increase capital as confidence grows

### If Stock Backtest Shows Strong Performance

1. **Fundamental Check:** Verify fundamentals support the move
2. **Entry Timing:** Use `/dip` to find better entry price
3. **Position Sizing:** Calculate optimal position size
4. **Exit Plan:** Set profit target and stop loss

---

## ⚠️ Important Disclaimers

### Backtesting Limitations

1. **Past ≠ Future:** Historical performance doesn't guarantee future results
2. **No Execution Costs:** Backtests assume perfect fills, no slippage
3. **No Market Impact:** Assumes your trades don't move the market
4. **Fundamental Changes:** Uses real-time fundamentals (not historical snapshots)
5. **Survivorship Bias:** Only tests stocks currently in database

### Best Practices

✅ **DO:**
- Run multiple backtests (different periods, parameters)
- Compare to benchmark (S&P 500)
- Validate with recent data (last 30-90 days)
- Paper trade before real money
- Start small and scale gradually

❌ **DON'T:**
- Over-optimize parameters (curve fitting)
- Assume backtests are predictive
- Deploy full capital immediately
- Ignore risk metrics (drawdown, volatility)
- Trade without stop losses

---

## 📈 Example Analysis Workflow

### Comprehensive Strategy Validation

```bash
# Step 1: Test momentum strategy (existing)
/backtest days:90

# Step 2: Test dip strategy (new!)
/backtest-dip days:90

# Step 3: Compare individual stocks
/backtest-stock AAPL days:90
/backtest-stock MSFT days:90
/backtest-stock NVDA days:90

# Step 4: Analyze results
# - Which strategy performed best?
# - Which had better risk-adjusted returns?
# - Which stocks outperformed?

# Step 5: Make decision
# - Portfolio: Momentum or Dip?
# - Individual picks: Which stocks?
# - Position sizing: Based on backtest performance
```

---

## 🎓 Economic Theory

### Why Backtest?

**Scientific Method for Trading:**
```
Hypothesis → Test → Analyze → Decide

Example:
1. Hypothesis: "Dip-buying works for quality stocks"
2. Test: /backtest-dip (90 days)
3. Analyze: 12% return, 64% win rate
4. Decide: Strategy valid, deploy with 20% capital
```

**Confidence Through Data:**
- Removes emotion from decision-making
- Quantifies expected returns
- Measures risk (volatility, drawdown)
- Identifies optimal parameters

---

## 📝 Code Architecture

### DipBacktester Class

```python
class DipBacktester:
    """
    Tests dip-buying strategy:
    1. Find dips each day (historical scoring)
    2. Buy top candidates (position sizing)
    3. Hold for N days (exit timing)
    4. Track performance (metrics)
    """
    
    def find_dip_candidates_at_date(target_date):
        # Only uses data BEFORE target_date
        # Prevents lookahead bias
        
    def run_backtest(start_date, end_date, capital, hold_days):
        # Simulates real trading
        # Returns comprehensive results
```

### StockBacktester Class

```python
class StockBacktester:
    """
    Tests buy-and-hold for individual stocks:
    1. Buy at start date
    2. Hold to end date
    3. Calculate returns, risk metrics
    4. Analyze news sentiment
    """
    
    def backtest_stock(ticker, start_date, end_date, capital):
        # Simple buy-and-hold
        # Useful for comparison
```

---

## 🔄 Integration with Existing Features

### Workflow: Find → Validate → Execute

```
1. Find Opportunities
   ├── /daily (momentum picks)
   └── /dip (contrarian picks)

2. Validate Strategy
   ├── /backtest (momentum historical)
   ├── /backtest-dip (dip historical)
   └── /backtest-stock TICKER (individual)

3. Deep Dive
   └── /stock TICKER (current analysis)

4. Execute (Manual - Outside Bot)
   ├── Place orders via broker
   ├── Set stop losses
   └── Monitor performance
```

---

## 🎯 Success Metrics

### Dip Strategy Goals

```
Target Performance (90-day):
- Total Return: > 8%
- Win Rate: > 60%
- Avg Win/Loss: > 2:1
- Max Drawdown: < 15%
- Sharpe Ratio: > 1.5
```

### Individual Stock Goals

```
Target vs. S&P 500:
- Outperform by > 3%
- Lower volatility (< 25%)
- Max drawdown < 20%
- Positive news sentiment
```

---

## 📚 Related Documentation

- **`BUY_THE_DIP_GUIDE.md`** - Dip strategy explanation
- **`BACKTESTING_GUIDE.md`** - Portfolio backtest guide
- **`SMARTINVEST_COMPLETE_GUIDE.md`** - Full system overview

---

**Ready to test your strategies with real data!** 🚀

*Document Last Updated: November 13, 2025*

