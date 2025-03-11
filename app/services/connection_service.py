from sqlalchemy.orm import Session
from app.models.connection import Connection
from typing import Optional, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.services.schema_service import SchemaService
from app.core.database import get_db

class ConnectionService:
    def __init__(self, db: Session = None):
        self.db = db if db is not None else next(get_db())
    
    def get_connection(self, connection_id: int, user_id: int) -> Optional[Connection]:
        """Get a connection by ID and verify ownership"""
        return self.db.query(Connection).filter(
            Connection.id == connection_id,
            Connection.user_id == user_id
        ).first()
    
    def get_user_connections(self, user_id: int) -> list[Connection]:
        """Get all connections for a user."""
        return self.db.query(Connection).filter(Connection.user_id == user_id).all()
    
    def test_connection(self, connection_data: Dict) -> tuple[bool, str]:
        """Test if the connection can be established"""
        try:
            # Create connection URL based on database type
            if connection_data["db_type"].lower() == "mysql":
                url = f"mysql+mysqlconnector://{connection_data['username']}:{connection_data['password']}@{connection_data['host']}:{connection_data['port']}/{connection_data['database']}"
            else:
                return False, f"Database type {connection_data['db_type']} not supported"

            # Try to connect and get schema information
            engine = create_engine(url)
            with engine.connect() as conn:
                # Test if we can query the database
                conn.execute(text("SELECT 1"))
                
                # Get schema information
                schema_service = SchemaService(url, connection_data["db_type"], connection_data["database"])
                schema_info = schema_service.format_schema_for_prompt()
                
                return True, schema_info
        except SQLAlchemyError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def create_connection(self, user_id: int, connection_data: Dict) -> tuple[Optional[Connection], str]:
        """Create a new connection after testing it"""
        success, message = self.test_connection(connection_data)
        
        if not success:
            return None, message

        try:
            # Create new connection
            new_connection = Connection(
                name=connection_data["name"],
                db_type=connection_data["db_type"],
                host=connection_data["host"],
                port=connection_data["port"],
                username=connection_data["username"],
                password=connection_data["password"],
                database=connection_data["database"],
                user_id=user_id,
                schema_info=message  # Store the schema information
            )
            
            self.db.add(new_connection)
            self.db.commit()
            self.db.refresh(new_connection)
            
            return new_connection, "Connection created successfully"
        except Exception as e:
            self.db.rollback()
            return None, f"Failed to create connection: {str(e)}"
    
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
    
    def delete_connection(self, connection_id: int, user_id: int) -> bool:
        """Delete a connection"""
        connection = self.get_connection(connection_id, user_id)
        if connection:
            self.db.delete(connection)
            self.db.commit()
            return True
        return False 