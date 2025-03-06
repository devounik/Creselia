from sqlalchemy import Column, Integer, String, DateTime, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    engine = Column(String)  # postgresql, mysql, sqlite
    host = Column(String)
    port = Column(Integer)
    database = Column(String)
    username = Column(String)
    password = Column(String)
    schema = Column(JSON)  # Stores the database schema
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, index=True)
    natural_query = Column(String)
    sql_query = Column(String)
    execution_time = Column(Float)
    status = Column(String)  # success, error
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow) 