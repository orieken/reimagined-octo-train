# app/database/session.py
"""
Database session management for the Friday service
"""
import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

logger = logging.getLogger("friday.database")

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    # These parameters should be adjusted based on your needs
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args={}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Get a database session

    This function is used for dependency injection in FastAPI routes.
    It yields a session and ensures it's closed after use.

    Yields:
        SQLAlchemy session
    """
    db = SessionLocal()
    try:
        logger.debug("Database session created")
        yield db
    finally:
        db.close()
        logger.debug("Database session closed")
