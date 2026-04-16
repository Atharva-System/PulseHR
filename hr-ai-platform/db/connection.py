"""Database connection — SQLAlchemy async engine + session factory."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# --- Engine (singleton) ---

_engine = None


def get_engine():
    """Return a singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False,
        )
        logger.info("Database engine created")
    return _engine


# --- Session factory ---

_session_factory = None


def get_session_factory() -> sessionmaker:
    """Return a configured session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def get_db_session() -> Session:
    """Yield a database session (for use in with-statement)."""
    factory = get_session_factory()
    return factory()
