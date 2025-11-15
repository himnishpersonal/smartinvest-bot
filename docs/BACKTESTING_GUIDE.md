# Portfolio Backtesting Guide

## Overview

The SmartInvest backtesting system allows you to simulate how your recommendation strategy would have performed historically. This validates the ML model's effectiveness and provides concrete performance metrics.

---

## Quick Start

### Discord Command

```
/backtest
/backtest days:90
/backtest days:180 capital:25000 hold_days:10
```

### Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `days` | 90 | 30-365 | Number of days to backtest |
| `capital` | 10000 | 1K-1M | Starting capital in dollars |
| `hold_days` | 5 | 1-30 | Days to hold each position |

---

## How It Works

### 1. Historical Simulation

The backtest simulates trading over a historical period:

```
For each day in backtest period:
  1. Score all stocks using ONLY past data (no lookahead bias)
  2. Select top 10 highest-scoring stocks
  3. Buy equal-weight positions if:
     - Score ≥ 70
     - Have available cash
     - Under max positions (10)
  4. Hold for specified days (default: 5)
  5. Sell and calculate profit/loss
  6. Track portfolio value
```

### 2. No Lookahead Bias

**Critical:** The system NEVER uses future data when scoring past dates.

- When scoring stocks on 2024-08-01:
  - Uses price data through 2024-07-31 only
  - Uses news articles published before 2024-08-01 only
  - ML model sees same features it would have in real-time

This ensures backtest results are realistic and not artificially inflated.

### 3. Portfolio Management

- **Max Positions:** 10 concurrent positions
- **Position Sizing:** Equal weight (cash / available_slots)
- **Entry:** Only stocks with score ≥ 70
- **Exit:** Automatic after hold_days period
- **Rebalancing:** Daily check for exits, then new entries

---

## Output Metrics

### Returns

```
Starting Capital:  $10,000
Ending Value:      $12,450
Total Return:      +24.5%
S&P 500 Return:    +8.2%
Alpha:             +16.3% (outperformance)
```

**Alpha** = Your return - S&P 500 return (measures skill vs market)

### Trade Statistics

```
Total Trades:   54
Winners:        42 (78%)
Losers:         12 (22%)
Avg Win:        +5.8%
Avg Loss:       -2.3%
Avg Hold:       5.0 days
```

- **Win Rate:** % of profitable trades (higher is better, 60%+ is good)
- **Avg Win/Loss:** Expectancy of each trade type
- **Win Rate × Avg Win > Loss Rate × Avg Loss** = Profitable system

### Risk Metrics

```
Sharpe Ratio:   2.14
Max Drawdown:   -8.4%
Profit Factor:  2.8
```

#### Sharpe Ratio
Risk-adjusted returns. Higher is better.
- < 1.0: Poor
- 1.0-2.0: Good
- 2.0-3.0: Very good
- > 3.0: Excellent

Formula: `(Avg Return - Risk Free Rate) / Std Deviation × √252`

#### Max Drawdown
Worst peak-to-trough decline during backtest.
- Measures worst-case loss if you entered at peak
- Lower is better (less risky)
- -10% is acceptable, -20% is concerning, -30%+ is dangerous

#### Profit Factor
Total wins / Total losses
- > 2.0: Strong system
- 1.5-2.0: Good system
- 1.0-1.5: Marginal system
- < 1.0: Losing system

---

## Visualizations

### 1. Equity Curve
Shows portfolio value over time vs S&P 500 benchmark.

**What to look for:**
- Upward trend (profitable)
- Smooth curve (consistent)
- Above benchmark line (outperforming)

### 2. Drawdown Chart
Shows distance from peak value over time.

**What to look for:**
- Shallow drawdowns (less risky)
- Quick recovery (resilient)
- Max drawdown magnitude

### 3. Trade Distribution
Histogram of trade returns.

**What to look for:**
- More bars on right (positive) side
- Mean line > 0
- Normal distribution shape

---

## Interpreting Results

### Excellent Performance
```
Total Return:  > 15%
Win Rate:      > 70%
Sharpe Ratio:  > 2.0
Max Drawdown:  < -10%
```
✅ Strategy is working very well. Consider live trading.

### Good Performance
```
Total Return:  5-15%
Win Rate:      60-70%
Sharpe Ratio:  1.5-2.0
Max Drawdown:  -10% to -15%
```
✅ Strategy has positive edge. Monitor and refine.

### Marginal Performance
```
Total Return:  0-5%
Win Rate:      50-60%
Sharpe Ratio:  1.0-1.5
Max Drawdown:  -15% to -20%
```
⚠️ Strategy is barely profitable. Needs improvement.

### Poor Performance
```
Total Return:  < 0%
Win Rate:      < 50%
Sharpe Ratio:  < 1.0
Max Drawdown:  > -20%
```
❌ Strategy is losing money. Significant changes needed.

---

## Example Usage

### Basic Backtest (90 days)
```
/backtest
```

**Use Case:** Quick validation of current model performance

### Extended Backtest (6 months)
```
/backtest days:180
```

**Use Case:** Test across different market conditions

### Large Capital Simulation
```
/backtest capital:100000
```

**Use Case:** See how strategy scales with more money

### Longer Hold Period
```
/backtest hold_days:10
```

**Use Case:** Test if holding longer improves returns

---

## Limitations & Caveats

### 1. Transaction Costs Not Included
- Real trading has slippage (~0.05-0.1% per trade)
- For 54 trades: ~0.05% × 54 = -2.7% cost
- Add this to your mental model

### 2. Survivorship Bias
- Database contains TODAY'S stocks, not historical constituents
- Some stocks may have been delisted
- Impact is usually minor for S&P 500 (low turnover)

### 3. Limited Historical Data
- Can only backtest as far as your data goes
- Most stocks: 5 years of history
- News sentiment: May have gaps in older data

### 4. Market Regime Dependence
- Performance varies by market conditions
- Bull market: Easier to make money
- Bear market: Harder, but separates good from bad systems
- Test across different periods

### 5. Overfitting Risk
- Good backtest ≠ guaranteed future performance
- ML model may have overfit to training data
- Always validate with out-of-sample period

---

## Advanced Tips

### 1. Test Multiple Periods

```
/backtest days:60   # Recent (Aug-Nov 2024)
/backtest days:180  # Medium-term (May-Nov 2024)
/backtest days:365  # Long-term (Nov 2023-2024)
```

**Why:** Ensures consistency across different market environments.

### 2. Compare Hold Periods

```
/backtest hold_days:3
/backtest hold_days:5
/backtest hold_days:10
```

**Why:** Find optimal holding period for your strategy.

### 3. Stress Test with Smaller Capital

```
/backtest capital:5000
```

**Why:** See if strategy works with realistic starter capital.

### 4. Look for Red Flags

- Win rate < 50%: Strategy has no edge
- Sharpe < 1.0: Too much risk for the return
- Max DD > -25%: Unacceptable risk
- Only 1-2 trades: Not enough data, extend period

### 5. Compare to Buy-and-Hold

If your backtest shows:
- Total Return: +12%
- S&P 500: +8%

Ask: "Is +4% alpha worth the extra effort vs just buying SPY?"

---

## Troubleshooting

### "No trades executed"
**Cause:** No stocks scored ≥ 70 during period
**Solution:** 
- Check if ML model is loaded
- Extend backtest period
- Lower threshold in code (default: 70)

### "Backtest takes too long (>2 min)"
**Cause:** Large backtest period + many stocks
**Solution:**
- Reduce days (try 60 instead of 365)
- System needs optimization

### "All trades are losers"
**Cause:** Poor model or bad market period
**Solution:**
- Check model is trained correctly
- Try different time period
- Review feature engineering

### "Results seem too good"
**Cause:** Possible lookahead bias (bug)
**Solution:**
- Check database query dates
- Verify features use past data only
- Report if suspicious

---

## Best Practices

### ✅ Do's

1. **Run multiple backtests** with different parameters
2. **Check results make sense** (30% monthly return = suspicious)
3. **Look at charts** not just numbers
4. **Compare to benchmark** (S&P 500)
5. **Consider transaction costs** mentally
6. **Test recent periods** (more relevant)
7. **Document your findings** for future reference

### ❌ Don'ts

1. **Don't cherry-pick** best backtest period
2. **Don't ignore max drawdown** (risk matters!)
3. **Don't assume past = future** (markets change)
4. **Don't trade immediately** after one good backtest
5. **Don't backtest tiny periods** (<30 days = not enough data)
6. **Don't use results as guarantees** (past ≠ future performance)

---

## Next Steps

### If Backtest is Good (>10% return, 70%+ win rate)

1. **Validate with forward testing**
   - Run backtest on most recent 30 days
   - Compare to earlier periods
   - Consistency = good sign

2. **Paper trade for 1-2 months**
   - Follow recommendations in real-time
   - Track actual results vs predictions
   - Don't use real money yet

3. **Start small if live trading**
   - Begin with $1-5K
   - Max 2-3 positions
   - Learn risk management

### If Backtest is Poor (<5% return or negative)

1. **Review model training**
   - `python scripts/train_model_v2.py`
   - Check training accuracy
   - May need more data

2. **Adjust strategy**
   - Try different hold periods
   - Refine entry threshold
   - Add more features

3. **Debug feature engineering**
   - Are indicators calculating correctly?
   - Is sentiment analysis working?
   - Check for data quality issues

---

## Technical Details

### Code Location

- **Backtester:** `models/backtester.py`
- **Performance:** `utils/performance.py`
- **Visualizer:** `utils/visualizer.py`
- **Discord Command:** `bot_with_real_data.py` → `/backtest`

### Test Locally

```bash
# Run test backtest (60 days, no Discord)
python scripts/test_backtest.py
```

This validates the system works before using Discord command.

---

## FAQ

**Q: How long does a backtest take?**
A: 30-90 seconds for 90 days, ~2-3 minutes for 365 days.

**Q: Can I backtest specific stocks?**
A: Not yet (v1 only does portfolio of top 10). Coming in v2.

**Q: Why doesn't my backtest match real-time?**
A: Different data availability. Backtest uses what was known historically.

**Q: What if I get an error?**
A: Check logs, ensure stocks are loaded, run `test_backtest.py` first.

**Q: Can I save backtest results?**
A: Charts are saved as PNG files. Results are shown in Discord only (no DB storage yet).

**Q: How do I know if my backtest is valid?**
A: Compare multiple periods. If wildly different, may be overfitting.

---

## Resources

- **Backtesting Best Practices:** https://www.quantstart.com/articles/Backtesting-Trading-Strategies
- **Sharpe Ratio Explained:** https://www.investopedia.com/terms/s/sharperatio.asp
- **Maximum Drawdown:** https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp

---

**Version:** 1.0  
**Last Updated:** November 11, 2025  
**Author:** SmartInvest Team

