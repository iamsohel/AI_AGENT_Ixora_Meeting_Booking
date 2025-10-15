"""Database connection and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from .models import Base

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ixora_chat.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False  # Set to True for SQL logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database - create all tables."""
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at {DATABASE_URL}")


def get_db() -> Session:
    """
    Get database session.

    Yields:
        Session: SQLAlchemy session

    Usage:
        ```python
        db = next(get_db())
        try:
            # Use db
            pass
        finally:
            db.close()
        ```

    Or with FastAPI dependency injection:
        ```python
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a database session for non-FastAPI contexts.

    Returns:
        Session: SQLAlchemy session

    Note: Remember to close the session when done!
    """
    return SessionLocal()
