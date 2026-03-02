from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import config
from app.infra.db.models import Base

DATABASE_URL = config.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all tables from ORM models. Safe to call at startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
