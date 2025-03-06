from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from typing import Generator

# Create MySQL engine
engine = create_engine(
    settings.MYSQL_URL,
    pool_size=settings.MAX_CONNECTIONS_COUNT,
    max_overflow=0,
    pool_pre_ping=True  # Enable automatic reconnection
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Initialize database
def init_db() -> None:
    """Initialize the database, creating all tables"""
    try:
        # Create database if it doesn't exist
        temp_engine = create_engine(
            f"mysql+mysqlconnector://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}"
        )
        with temp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DATABASE}"))
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        raise Exception(f"Failed to initialize database: {str(e)}")

# Dependency for FastAPI
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 