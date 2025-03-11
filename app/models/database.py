from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    connection_id = Column(Integer, ForeignKey("connections.id", ondelete="CASCADE"))
    natural_query = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=False)
    execution_time = Column(Float)
    status = Column(String(50))  # success, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    connection = relationship("Connection", back_populates="queries")
    user = relationship("User", back_populates="query_history") 