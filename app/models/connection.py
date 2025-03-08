from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, event, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base, encrypt_value, decrypt_value

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
    schema = Column(JSON)  # Stores the database schema
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="connections")
    
    # Relationship with queries
    queries = relationship("QueryHistory", back_populates="connection", cascade="all, delete-orphan")

    @property
    def password(self):
        """Decrypt password when accessing"""
        return decrypt_value(self._password) if self._password else None

    @password.setter
    def password(self, value):
        """Encrypt password when setting"""
        self._password = encrypt_value(value) if value else None

    def __repr__(self):
        return f"<Connection {self.name} ({self.db_type})>" 