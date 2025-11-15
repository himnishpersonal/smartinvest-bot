#!/usr/bin/env python3
"""
Exit Signal Monitoring Script

Runs daily to:
1. Check all open positions for exit signals
2. Generate alerts for profit targets, stop losses, reversals, etc.
3. Send Discord notifications (if alerts enabled)
4. Update position statuses

Should be run via cron job alongside daily_refresh.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime
from typing import List
import time

from config import Config
from data.storage import DatabaseManager
from models.exit_signals import ExitSignalDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def monitor_all_positions(db: DatabaseManager, detector: ExitSignalDetector) -> dict:
    """
    Monitor all open positions and generate exit signals.
    
    Args:
        db: DatabaseManager instance
        detector: ExitSignalDetector instance
        
    Returns:
        Dictionary with monitoring statistics
    """
    logger.info("Starting exit signal monitoring...")
    
    # Get all open positions
    open_positions = db.get_all_open_positions()
    
    if not open_positions:
        logger.info("No open positions to monitor")
        return {
            'total_positions': 0,
            'positions_checked': 0,
            'signals_generated': 0,
            'high_urgency': 0,
            'medium_urgency': 0,
            'low_urgency': 0
        }
    
    logger.info(f"Found {len(open_positions)} open positions to monitor")
    
    stats = {
        'total_positions': len(open_positions),
        'positions_checked': 0,
        'signals_generated': 0,
        'high_urgency': 0,
        'medium_urgency': 0,
        'low_urgency': 0,
        'errors': 0
    }
    
    # Process each position
    for position in open_positions:
        try:
            # Get stock info
            session = db.Session()
            stock = session.query(db.Stock).filter_by(id=position.stock_id).first()
            session.close()
            
            if not stock:
                logger.warning(f"Stock {position.stock_id} not found for position {position.id}")
                stats['errors'] += 1
                continue
            
            ticker = stock.ticker
            logger.info(f"Checking position: {ticker} (User: {position.discord_user_id[:8]}...)")
            
            # Get current price
            current_price = detector.get_current_price(ticker)
            if current_price is None:
                logger.warning(f"Could not fetch price for {ticker}")
                stats['errors'] += 1
                continue
            
            # Get price data for technical analysis
            price_data = detector.get_price_data(ticker, days=30)
            
            # Get current sentiment
            sentiment = detector.get_current_sentiment(stock.id, days=7)
            
            # Check for exit signals
            signals = detector.check_position_for_exits(
                position=position,
                current_price=current_price,
                price_data=price_data,
                news_sentiment=sentiment
            )
            
            stats['positions_checked'] += 1
            
            # Create exit signals in database
            for signal_data in signals:
                try:
                    # Check if signal already exists (avoid duplicates)
                    existing = check_existing_signal(db, position.id, signal_data['type'])
                    if existing:
                        logger.debug(f"Signal {signal_data['type']} already exists for position {position.id}")
                        continue
                    
                    # Create new signal
                    db.create_exit_signal(
                        position_id=position.id,
                        signal_type=signal_data['type'],
                        current_price=signal_data['current_price'],
                        reason=signal_data['reason'],
                        urgency=signal_data['urgency'],
                        target_price=signal_data.get('target_price'),
                        technical_signals=signal_data.get('technical_signals', {}),
                        sentiment_data=signal_data.get('sentiment_data', {})
                    )
                    
                    stats['signals_generated'] += 1
                    
                    # Count by urgency
                    if signal_data['urgency'] == 'high':
                        stats['high_urgency'] += 1
                    elif signal_data['urgency'] == 'medium':
                        stats['medium_urgency'] += 1
                    else:
                        stats['low_urgency'] += 1
                    
                    logger.info(f"✅ Created {signal_data['urgency']} urgency {signal_data['type']} signal for {ticker}")
                
                except Exception as e:
                    logger.error(f"Error creating signal for {ticker}: {e}")
                    stats['errors'] += 1
            
            # Rate limiting
            time.sleep(0.3)
        
        except Exception as e:
            logger.error(f"Error monitoring position {position.id}: {e}")
            stats['errors'] += 1
            continue
    
    return stats


def check_existing_signal(db: DatabaseManager, position_id: int, signal_type: str) -> bool:
    """
    Check if a pending signal of this type already exists for the position.
    
    Args:
        db: DatabaseManager instance
        position_id: Position ID
        signal_type: Signal type to check
        
    Returns:
        True if signal exists, False otherwise
    """
    try:
        session = db.Session()
        existing = session.query(db.ExitSignal)\
            .filter_by(position_id=position_id, signal_type=signal_type, status='pending')\
            .first()
        session.close()
        return existing is not None
    except Exception as e:
        logger.error(f"Error checking existing signal: {e}")
        return False


def expire_old_signals(db: DatabaseManager, days: int = 7) -> int:
    """
    Expire old pending signals that haven't been acted upon.
    
    Args:
        db: DatabaseManager instance
        days: Number of days before expiring
        
    Returns:
        Number of signals expired
    """
    try:
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        session = db.Session()
        old_signals = session.query(db.ExitSignal)\
            .filter_by(status='pending')\
            .filter(db.ExitSignal.signal_date < cutoff_date)\
            .all()
        
        count = 0
        for signal in old_signals:
            signal.status = 'expired'
            count += 1
        
        session.commit()
        session.close()
        
        logger.info(f"Expired {count} old signals")
        return count
    
    except Exception as e:
        logger.error(f"Error expiring old signals: {e}")
        return 0


def print_summary(stats: dict):
    """
    Print summary of exit signal monitoring.
    
    Args:
        stats: Statistics dictionary
    """
    logger.info("\n" + "="*60)
    logger.info("EXIT SIGNAL MONITORING SUMMARY")
    logger.info("="*60)
    logger.info(f"Total Positions: {stats['total_positions']}")
    logger.info(f"Positions Checked: {stats['positions_checked']}")
    logger.info(f"Signals Generated: {stats['signals_generated']}")
    logger.info(f"  High Urgency: {stats['high_urgency']}")
    logger.info(f"  Medium Urgency: {stats['medium_urgency']}")
    logger.info(f"  Low Urgency: {stats['low_urgency']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info("="*60 + "\n")


def main():
    """Main execution function."""
    logger.info("="*60)
    logger.info("Starting Exit Signal Monitoring")
    logger.info("="*60 + "\n")
    
    # Initialize components
    config = Config()
    db = DatabaseManager(config.DATABASE_URL)
    detector = ExitSignalDetector(db)
    
    try:
        # Monitor all positions and generate signals
        stats = monitor_all_positions(db, detector)
        
        # Expire old signals
        expired = expire_old_signals(db, days=7)
        stats['expired_signals'] = expired
        
        # Print summary
        print_summary(stats)
        
        logger.info("Exit signal monitoring completed successfully!")
        return 0
    
    except Exception as e:
        logger.error(f"Exit signal monitoring failed: {e}", exc_info=True)
        return 1
    
    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())

