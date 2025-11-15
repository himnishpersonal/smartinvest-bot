"""
Database connection and session management utilities.
"""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

from .schema import Base

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///smartinvest.db')

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)


def init_db():
    """
    Initialize the database by creating all tables.
    """
    Base.metadata.create_all(engine)
    print("✅ Database tables created successfully!")


def drop_db():
    """
    Drop all tables from the database. Use with caution!
    """
    Base.metadata.drop_all(engine)
    print("⚠️  All database tables dropped!")


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    Automatically handles commit/rollback and session cleanup.
    
    Usage:
        with get_db_session() as session:
            stock = session.query(Stock).filter_by(ticker='AAPL').first()
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_session():
    """
    Get a new database session.
    Remember to close the session when done!
    
    Returns:
        Session: SQLAlchemy session object
    """
    return Session()


def close_session(session):
    """
    Close a database session.
    
    Args:
        session: SQLAlchemy session object
    """
    session.close()


# For convenience in imports
__all__ = [
    'engine',
    'Session',
    'init_db',
    'drop_db',
    'get_db_session',
    'get_session',
    'close_session'
]

