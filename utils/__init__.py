"""
Utility functions for SmartInvest Bot
"""
from .helpers import (
    is_market_open,
    next_market_open,
    format_time_ago,
    validate_ticker,
    validate_score_range,
    sanitize_sql_input,
    format_price,
    format_percentage,
    format_large_number,
    truncate_text,
    calculate_return,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    handle_errors
)

__all__ = [
    'is_market_open',
    'next_market_open',
    'format_time_ago',
    'validate_ticker',
    'validate_score_range',
    'sanitize_sql_input',
    'format_price',
    'format_percentage',
    'format_large_number',
    'truncate_text',
    'calculate_return',
    'calculate_sharpe_ratio',
    'calculate_max_drawdown',
    'handle_errors'
]