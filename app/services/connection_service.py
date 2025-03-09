from sqlalchemy.orm import Session
from app.models.connection import Connection
from typing import Optional

class ConnectionService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_connection(self, connection_id: int) -> Optional[Connection]:
        """Get a database connection by ID."""
        return self.db.query(Connection).filter(Connection.id == connection_id).first()
    
    def get_user_connections(self, user_id: int) -> list[Connection]:
        """Get all connections for a user."""
        return self.db.query(Connection).filter(Connection.user_id == user_id).all()
    
    def create_connection(self, user_id: int, connection_data: dict) -> Connection:
        """Create a new database connection."""
        connection = Connection(
            user_id=user_id,
            name=connection_data["name"],
            description=connection_data.get("description", ""),
            db_type=connection_data["db_type"],
            host=connection_data["host"],
            port=connection_data["port"],
            database=connection_data["database"],
            username=connection_data["username"],
            password=connection_data["password"]
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection
    
    def update_connection(self, connection_id: int, connection_data: dict) -> Optional[Connection]:
        """Update an existing database connection."""
        connection = self.get_connection(connection_id)
        if not connection:
            return None
        
        for key, value in connection_data.items():
            if hasattr(connection, key):
                setattr(connection, key, value)
        
        self.db.commit()
        self.db.refresh(connection)
        return connection
    
    def delete_connection(self, connection_id: int) -> bool:
        """Delete a database connection."""
        connection = self.get_connection(connection_id)
        if not connection:
            return False
        
        self.db.delete(connection)
        self.db.commit()
        return True 