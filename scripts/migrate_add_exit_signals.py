#!/usr/bin/env python3
"""
Database migration script to add exit signal tracking tables.

This script:
1. Adds the 'user_positions' table
2. Adds the 'exit_signals' table  
3. Sets up relationships and indexes
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from config import Config
from data.storage import DatabaseManager
from data.schema import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the migration."""
    logger.info("="*60)
    logger.info("MIGRATION: Add Exit Signal Tracking")
    logger.info("="*60)
    
    try:
        # Initialize database
        config = Config()
        db = DatabaseManager(config.DATABASE_URL)
        
        logger.info("Creating new tables and columns...")
        
        # Create all tables (this will create new ones, skip existing)
        Base.metadata.create_all(db.engine)
        
        logger.info("✅ Migration completed successfully!")
        logger.info("\nNew features added:")
        logger.info("  • user_positions table - Track your actual trades")
        logger.info("  • exit_signals table - Automatic exit signal detection")
        logger.info("  • Position management (add, close, monitor)")
        logger.info("  • Exit signal detection (profit targets, stop losses, reversals)")
        logger.info("\nNew Discord commands:")
        logger.info("  • /position add/close - Manage your positions")
        logger.info("  • /positions - View open positions")
        logger.info("  • /exits - View active exit signals")
        logger.info("  • /track - Your trading performance")
        logger.info("\nNext steps:")
        logger.info("  1. Restart your Discord bot")
        logger.info("  2. Use /position add to start tracking trades")
        logger.info("  3. Check /exits daily for profit/loss signals")
        logger.info("  4. View your performance with /track")
        logger.info("\nAutomatic monitoring:")
        logger.info("  • Exit signals generated daily via cron job")
        logger.info("  • Profit targets, stop losses, technical reversals detected")
        logger.info("  • Completely automated - no manual work needed!")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

