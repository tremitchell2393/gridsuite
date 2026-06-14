from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _build_db_url(url: str) -> str:
    """Convert postgresql:// URL to use pg8000 driver with SSL."""
    url = url.replace("postgresql://", "postgresql+pg8000://", 1)
    url = url.replace("postgres://", "postgresql+pg8000://", 1)
    if "ssl" not in url:
        url += "?ssl=require"
    return url


engine = create_engine(_build_db_url(settings.DATABASE_URL), pool_pre_ping=True, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
