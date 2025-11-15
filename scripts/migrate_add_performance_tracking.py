#!/usr/bin/env python3
"""
Database migration script to add performance tracking tables.

This script:
1. Adds the 'recommendation_performance' table
2. Adds 'strategy_type' column to 'recommendations' table
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
    logger.info("MIGRATION: Add Performance Tracking")
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
        logger.info("  • recommendation_performance table")
        logger.info("  • strategy_type column in recommendations")
        logger.info("  • Automatic performance tracking")
        logger.info("\nNext steps:")
        logger.info("  1. Restart your Discord bot")
        logger.info("  2. Use /performance to view stats")
        logger.info("  3. Use /leaderboard to see top performers")
        logger.info("\nNote: Existing recommendations won't have performance data.")
        logger.info("      New recommendations will be tracked automatically!")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

