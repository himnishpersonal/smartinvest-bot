"""
Backtest Visualization Tools
Creates charts for backtesting results
"""

import logging
from datetime import datetime
from typing import List, Dict
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for Discord
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

logger = logging.getLogger(__name__)


class BacktestVisualizer:
    """
    Creates visualizations for backtest results.
    """
    
    def __init__(self, style: str = 'dark_background'):
        """
        Initialize visualizer.
        
        Args:
            style: Matplotlib style ('dark_background' for Discord dark mode)
        """
        plt.style.use(style)
        self.colors = {
            'profit': '#00ff88',
            'loss': '#ff4444',
            'neutral': '#888888',
            'benchmark': '#4488ff'
        }
    
    def plot_equity_curve(self, equity_curve: List[Dict], benchmark_curve: List[Dict] = None,
                         filename: str = 'backtest_equity.png') -> str:
        """
        Plot portfolio value over time vs benchmark.
        
        Args:
            equity_curve: List of {date, value} dicts
            benchmark_curve: Optional benchmark data
            filename: Output filename
            
        Returns:
            Path to saved image
        """
        if not equity_curve:
            logger.warning("No equity curve data to plot")
            return None
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Portfolio line
        dates = [point['date'] for point in equity_curve]
        values = [point['value'] for point in equity_curve]
        
        ax.plot(dates, values, label='SmartInvest Portfolio', 
                linewidth=2.5, color=self.colors['profit'], zorder=3)
        
        # Benchmark line
        if benchmark_curve:
            bench_dates = [point['date'] for point in benchmark_curve]
            bench_values = [point['value'] for point in benchmark_curve]
            ax.plot(bench_dates, bench_values, label='S&P 500', 
                   linewidth=2, color=self.colors['benchmark'], 
                   linestyle='--', alpha=0.7, zorder=2)
        
        # Formatting
        ax.set_title('📈 Portfolio Performance', fontsize=18, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Portfolio Value ($)', fontsize=12)
        ax.legend(loc='upper left', fontsize=11, framealpha=0.9)
        ax.grid(alpha=0.2, linestyle='--')
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.xticks(rotation=45, ha='right')
        
        # Add starting/ending value annotations
        start_val = values[0]
        end_val = values[-1]
        return_pct = ((end_val - start_val) / start_val) * 100
        
        ax.annotate(f'Start: ${start_val:,.0f}', 
                   xy=(dates[0], start_val),
                   xytext=(10, 20), textcoords='offset points',
                   fontsize=10, alpha=0.8,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='gray', alpha=0.3))
        
        ax.annotate(f'End: ${end_val:,.0f}\n({return_pct:+.1f}%)', 
                   xy=(dates[-1], end_val),
                   xytext=(-80, -30), textcoords='offset points',
                   fontsize=10, alpha=0.8,
                   bbox=dict(boxstyle='round,pad=0.5', 
                            facecolor=self.colors['profit'] if return_pct > 0 else self.colors['loss'], 
                            alpha=0.3))
        
        plt.tight_layout()
        plt.savefig(filename, dpi=120, bbox_inches='tight', facecolor='#2b2d31')
        plt.close()
        
        logger.info(f"Equity curve saved to {filename}")
        return filename
    
    def plot_drawdown(self, equity_curve: List[Dict], filename: str = 'backtest_drawdown.png') -> str:
        """
        Plot drawdown chart (distance from peak).
        
        Args:
            equity_curve: List of {date, value} dicts
            filename: Output filename
            
        Returns:
            Path to saved image
        """
        if not equity_curve:
            return None
        
        fig, ax = plt.subplots(figsize=(14, 5))
        
        dates = [point['date'] for point in equity_curve]
        values = [point['value'] for point in equity_curve]
        
        # Calculate drawdown
        peak = values[0]
        drawdowns = []
        for val in values:
            if val > peak:
                peak = val
            dd = ((val - peak) / peak) * 100
            drawdowns.append(dd)
        
        # Plot
        ax.fill_between(dates, drawdowns, 0, alpha=0.4, color=self.colors['loss'], label='Drawdown')
        ax.plot(dates, drawdowns, color=self.colors['loss'], linewidth=1.5)
        
        # Formatting
        ax.set_title('📉 Drawdown Analysis', fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('Date', fontsize=11)
        ax.set_ylabel('Drawdown (%)', fontsize=11)
        ax.grid(alpha=0.2, linestyle='--')
        
        # Format axes
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.xticks(rotation=45, ha='right')
        
        # Highlight max drawdown
        max_dd = min(drawdowns)
        max_dd_idx = drawdowns.index(max_dd)
        max_dd_date = dates[max_dd_idx]
        
        ax.plot(max_dd_date, max_dd, 'o', color='red', markersize=8, zorder=5)
        ax.annotate(f'Max DD: {max_dd:.1f}%', 
                   xy=(max_dd_date, max_dd),
                   xytext=(20, 20), textcoords='offset points',
                   fontsize=10,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='red', alpha=0.3),
                   arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
        
        plt.tight_layout()
        plt.savefig(filename, dpi=120, bbox_inches='tight', facecolor='#2b2d31')
        plt.close()
        
        logger.info(f"Drawdown chart saved to {filename}")
        return filename
    
    def plot_trade_distribution(self, trades: List[Dict], filename: str = 'backtest_trades.png') -> str:
        """
        Plot histogram of trade returns.
        
        Args:
            trades: List of trade dicts with 'pnl_pct'
            filename: Output filename
            
        Returns:
            Path to saved image
        """
        if not trades:
            return None
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        returns = [t['pnl_pct'] for t in trades]
        
        # Create histogram
        colors_list = [self.colors['profit'] if r > 0 else self.colors['loss'] for r in returns]
        
        n, bins, patches = ax.hist(returns, bins=25, alpha=0.7, 
                                    edgecolor='white', linewidth=0.5)
        
        # Color bars based on profit/loss
        for i, patch in enumerate(patches):
            if bins[i] < 0:
                patch.set_facecolor(self.colors['loss'])
            else:
                patch.set_facecolor(self.colors['profit'])
        
        # Zero line
        ax.axvline(x=0, color='white', linestyle='--', linewidth=2, 
                  label='Break-even', alpha=0.6)
        
        # Mean line
        mean_return = np.mean(returns)
        ax.axvline(x=mean_return, color='yellow', linestyle='-', linewidth=2,
                  label=f'Mean: {mean_return:+.2f}%', alpha=0.8)
        
        # Formatting
        ax.set_title('📊 Trade Return Distribution', fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('Return (%)', fontsize=12)
        ax.set_ylabel('Number of Trades', fontsize=12)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(alpha=0.2, axis='y', linestyle='--')
        
        # Format x-axis
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:+.1f}%'))
        
        # Add statistics text
        win_count = sum(1 for r in returns if r > 0)
        loss_count = len(returns) - win_count
        win_rate = (win_count / len(returns)) * 100 if returns else 0
        
        stats_text = (
            f"Total Trades: {len(returns)}\n"
            f"Winners: {win_count} ({win_rate:.1f}%)\n"
            f"Losers: {loss_count} ({100-win_rate:.1f}%)"
        )
        
        ax.text(0.02, 0.98, stats_text,
               transform=ax.transAxes,
               fontsize=10,
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='gray', alpha=0.3))
        
        plt.tight_layout()
        plt.savefig(filename, dpi=120, bbox_inches='tight', facecolor='#2b2d31')
        plt.close()
        
        logger.info(f"Trade distribution saved to {filename}")
        return filename
    
    def plot_monthly_returns(self, equity_curve: List[Dict], filename: str = 'backtest_monthly.png') -> str:
        """
        Plot monthly returns bar chart.
        
        Args:
            equity_curve: List of {date, value} dicts
            filename: Output filename
            
        Returns:
            Path to saved image
        """
        if not equity_curve or len(equity_curve) < 30:
            return None
        
        import pandas as pd
        
        # Convert to DataFrame and resample to monthly
        df = pd.DataFrame(equity_curve)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        monthly = df['value'].resample('M').last()
        monthly_returns = monthly.pct_change() * 100
        monthly_returns = monthly_returns.dropna()
        
        if len(monthly_returns) < 2:
            return None
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Bar colors based on profit/loss
        colors = [self.colors['profit'] if r > 0 else self.colors['loss'] 
                 for r in monthly_returns]
        
        x = range(len(monthly_returns))
        bars = ax.bar(x, monthly_returns, color=colors, alpha=0.7, edgecolor='white', linewidth=0.5)
        
        # Formatting
        ax.set_title('📅 Monthly Returns', fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Return (%)', fontsize=12)
        ax.grid(alpha=0.2, axis='y', linestyle='--')
        ax.axhline(y=0, color='white', linestyle='-', linewidth=1, alpha=0.5)
        
        # X-axis labels
        labels = [d.strftime('%b %y') for d in monthly_returns.index]
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        
        # Format y-axis
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'{y:+.1f}%'))
        
        plt.tight_layout()
        plt.savefig(filename, dpi=120, bbox_inches='tight', facecolor='#2b2d31')
        plt.close()
        
        logger.info(f"Monthly returns chart saved to {filename}")
        return filename

