from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base, encrypt_value, decrypt_value
import json
from typing import Optional, Dict, Any, Union

class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    db_type = Column(String(50), nullable=False)  # mysql, postgresql, sqlite
    host = Column(String(255))
    port = Column(Integer)
    database = Column(String(255))
    username = Column(String(255))
    _password = Column('password', String(255))  # Encrypted password
    _schema_info = Column('schema', Text)  # Stores the database schema and relationships
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="connections")
    
    # Relationship with queries
    queries = relationship("QueryHistory", back_populates="connection", cascade="all, delete-orphan")

    @property
    def password(self) -> Optional[str]:
        """Decrypt password when accessing"""
        if not self._password:
            return None
        try:
            return decrypt_value(self._password)
        except Exception as e:
            raise ValueError(f"Failed to decrypt password: {str(e)}")

    @password.setter
    def password(self, value: Optional[str]) -> None:
        """Encrypt password when setting"""
        if not value:
            self._password = None
            return
        try:
            self._password = encrypt_value(value)
        except Exception as e:
            raise ValueError(f"Failed to encrypt password: {str(e)}")

    @property
    def schema(self) -> Optional[str]:
        """Get schema information"""
        return self._schema_info

    @schema.setter
    def schema(self, value: Optional[Union[str, Dict]]) -> None:
        """Set schema information from either a string or dictionary"""
        if not value:
            self._schema_info = None
            return
        
        if isinstance(value, dict):
            self._schema_info = json.dumps(value)
        else:
            self._schema_info = value

    def __repr__(self):
        return f"<Connection {self.name} ({self.db_type})>" 