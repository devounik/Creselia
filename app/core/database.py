from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from typing import Generator
import mysql.connector
from mysql.connector import Error
from cryptography.fernet import Fernet
import base64
import os
from pathlib import Path

# Create the key file path in the app directory
key_file = Path("app/core/encryption.key")

# Generate or load encryption key
def get_encryption_key():
    if not key_file.exists():
        # Generate a new key if it doesn't exist
        key = Fernet.generate_key()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(key)
    return key_file.read_bytes()

# Create Fernet instance for encryption/decryption
fernet = Fernet(get_encryption_key())

def encrypt_value(value: str) -> str:
    if not value:
        return value
    return base64.b64encode(fernet.encrypt(value.encode())).decode()

def decrypt_value(encrypted_value: str) -> str:
    if not encrypted_value:
        return encrypted_value
    try:
        return fernet.decrypt(base64.b64decode(encrypted_value)).decode()
    except:
        return encrypted_value

def create_mysql_engine():
    """Create MySQL engine with the correct database"""
    try:
        # First create a connection without database
        mysql_conn = mysql.connector.connect(
            host=settings.MYSQL_HOST,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD
        )
        cursor = mysql_conn.cursor(dictionary=True)
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DATABASE}")
        cursor.execute(f"USE {settings.MYSQL_DATABASE}")
        mysql_conn.commit()
        
        # Check if database exists
        cursor.execute("SHOW DATABASES LIKE %s", (settings.MYSQL_DATABASE,))
        database_exists = cursor.fetchone() is not None
        
        if not database_exists:
            raise Exception(f"Failed to create database {settings.MYSQL_DATABASE}")
            
        cursor.close()
        mysql_conn.close()
        
        # Create SQLAlchemy engine with the database specified
        db_url = settings.MYSQL_URL
        print(f"Connecting to database with URL: {db_url}")
        
        return create_engine(
            db_url,
            pool_size=settings.MAX_CONNECTIONS_COUNT,
            max_overflow=0,
            pool_pre_ping=True,
            echo=True
        )
    except Error as e:
        print(f"Error creating MySQL engine: {e}")
        raise

# Create MySQL engine
engine = create_mysql_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db() -> None:
    """Initialize the database, creating tables if they don't exist"""
    try:
        # Import all models here to ensure they are registered with Base
        from app.models.connection import Connection
        from app.models.database import QueryHistory
        from app.models.user import User
        
        # Verify we can connect to the database
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DATABASE()"))
            database_name = result.scalar()
            print(f"Connected to database: {database_name}")
            
            # Create tables only if they don't exist
            Base.metadata.create_all(bind=engine, checkfirst=True)
            print(f"Database tables verified/created successfully in {database_name}!")
            
            # Show existing tables
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            print(f"Available tables: {', '.join(tables)}")

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise Exception(f"Failed to initialize database: {str(e)}")

# Dependency for FastAPI
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 