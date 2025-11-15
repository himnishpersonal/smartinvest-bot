#!/usr/bin/env python3
"""
Daily Performance Tracker Update Script

This script runs daily to:
1. Update performance metrics for all active recommendation trackers
2. Check progress on 1-day, 5-day, 10-day, and 30-day returns
3. Mark trackers as 'completed' when they reach 30 days
4. Log summary statistics

Should be run via cron job alongside daily_refresh.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime
from typing import List
import yfinance as yf
import time

from config import Config
from data.storage import DatabaseManager
from data.schema import RecommendationPerformance, Recommendation, Stock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_current_price(ticker: str) -> float:
    """
    Get current stock price from yfinance.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Current price or None if failed
    """
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period='1d')
        
        if data.empty:
            logger.warning(f"No data available for {ticker}")
            return None
        
        return float(data['Close'].iloc[-1])
    
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {e}")
        return None


def update_all_performance_trackers(db: DatabaseManager) -> dict:
    """
    Update all active performance trackers with current prices.
    
    Args:
        db: DatabaseManager instance
        
    Returns:
        Dictionary with update statistics
    """
    logger.info("Starting performance tracker updates...")
    
    # Get all active trackers
    active_trackers = db.get_active_performance_trackers()
    
    if not active_trackers:
        logger.info("No active performance trackers found")
        return {
            'total': 0,
            'updated': 0,
            'completed': 0,
            'failed': 0
        }
    
    logger.info(f"Found {len(active_trackers)} active trackers to update")
    
    stats = {
        'total': len(active_trackers),
        'updated': 0,
        'completed': 0,
        'failed': 0
    }
    
    # Process each tracker
    for tracker in active_trackers:
        try:
            # Get the stock ticker from the recommendation
            session = db.Session()
            try:
                recommendation = session.query(Recommendation)\
                    .filter_by(id=tracker.recommendation_id)\
                    .first()
                
                if not recommendation:
                    logger.warning(f"Recommendation {tracker.recommendation_id} not found")
                    stats['failed'] += 1
                    continue
                
                stock = session.query(Stock)\
                    .filter_by(id=recommendation.stock_id)\
                    .first()
                
                if not stock:
                    logger.warning(f"Stock {recommendation.stock_id} not found")
                    stats['failed'] += 1
                    continue
                
                ticker = stock.ticker
                
            finally:
                session.close()
            
            # Get current price
            current_price = get_current_price(ticker)
            
            if current_price is None:
                stats['failed'] += 1
                continue
            
            # Update tracker
            updated_tracker = db.update_performance_tracker(
                recommendation_id=tracker.recommendation_id,
                current_date=datetime.utcnow(),
                current_price=current_price
            )
            
            if updated_tracker:
                stats['updated'] += 1
                
                # Check if completed
                if updated_tracker.status == 'completed':
                    stats['completed'] += 1
                    logger.info(f"✓ {ticker}: Completed 30-day tracking (Return: {updated_tracker.return_30d:.2f}%)")
                else:
                    days_left = 30 - updated_tracker.days_tracked
                    logger.info(f"✓ {ticker}: Updated (Day {updated_tracker.days_tracked}/30, {days_left} days remaining)")
            else:
                stats['failed'] += 1
            
            # Rate limiting
            time.sleep(0.3)
        
        except Exception as e:
            logger.error(f"Error updating tracker {tracker.recommendation_id}: {e}")
            stats['failed'] += 1
            continue
    
    return stats


def print_summary(stats: dict):
    """
    Print summary of performance updates.
    
    Args:
        stats: Statistics dictionary
    """
    logger.info("\n" + "="*50)
    logger.info("PERFORMANCE UPDATE SUMMARY")
    logger.info("="*50)
    logger.info(f"Total Trackers: {stats['total']}")
    logger.info(f"Successfully Updated: {stats['updated']}")
    logger.info(f"Newly Completed: {stats['completed']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info("="*50 + "\n")


def main():
    """Main execution function."""
    logger.info("="*50)
    logger.info("Starting Daily Performance Tracker Update")
    logger.info("="*50 + "\n")
    
    # Initialize database
    config = Config()
    db = DatabaseManager(config)
    
    try:
        # Update all performance trackers
        stats = update_all_performance_trackers(db)
        
        # Print summary
        print_summary(stats)
        
        logger.info("Performance update completed successfully!")
        return 0
    
    except Exception as e:
        logger.error(f"Performance update failed: {e}", exc_info=True)
        return 1
    
    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())

