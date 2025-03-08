from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    connections = relationship("Connection", back_populates="user", overlaps="user")
    query_history = relationship("QueryHistory", secondary="connections", back_populates="user", overlaps="connection,queries,user")

    def __repr__(self):
        return f"<User {self.email}>" 