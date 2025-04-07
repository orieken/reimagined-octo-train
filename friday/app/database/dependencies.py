# app/database/dependencies.py
"""
Database dependencies for the Friday service
"""
from app.database.session import get_db

# Re-export get_db for easier imports
__all__ = ["get_db"]
