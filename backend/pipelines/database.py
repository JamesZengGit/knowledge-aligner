"""Database connection and models using SQLAlchemy."""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/slack_digest")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Initialize database with schema."""
    with open("schema.sql", "r") as f:
        schema = f.read()

    with engine.connect() as conn:
        conn.execute(text(schema))
        conn.commit()

def refresh_materialized_view():
    """Refresh the materialized view for daily summaries."""
    with engine.connect() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW daily_decisions_summary"))
        conn.commit()