from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.models.database import DatabaseConnection
from app.schemas.database import DatabaseConnectionCreate
from typing import List, Optional
import json
from datetime import datetime

class DatabaseService:
    def __init__(self, db: Session):
        self.db = db

    async def create_connection(self, connection: DatabaseConnectionCreate) -> DatabaseConnection:
        """Create a new database connection and store its details"""
        try:
            # Create connection string based on engine type
            if connection.engine == "sqlite":
                conn_str = f"sqlite:///{connection.database}"
            elif connection.engine == "postgresql":
                conn_str = f"postgresql://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
            elif connection.engine == "mysql":
                conn_str = f"mysql+mysqlconnector://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
            else:
                raise ValueError(f"Unsupported database engine: {connection.engine}")

            # Test connection
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                # Get database schema
                if connection.engine == "sqlite":
                    schema_query = """
                        SELECT name, sql FROM sqlite_master 
                        WHERE type='table' AND name NOT LIKE 'sqlite_%';
                    """
                elif connection.engine == "postgresql":
                    schema_query = """
                        SELECT table_name, column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public';
                    """
                else:  # MySQL
                    schema_query = """
                        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE 
                        FROM information_schema.columns 
                        WHERE table_schema = :database;
                    """
                
                result = conn.execute(schema_query)
                schema = [dict(row) for row in result]

            # Create database connection record
            db_connection = DatabaseConnection(
                name=connection.name,
                engine=connection.engine,
                host=connection.host,
                port=connection.port,
                database=connection.database,
                username=connection.username,
                password=connection.password,  # In production, encrypt this
                schema=schema,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self.db.add(db_connection)
            await self.db.commit()
            await self.db.refresh(db_connection)
            return db_connection

        except Exception as e:
            await self.db.rollback()
            raise Exception(f"Failed to create database connection: {str(e)}")

    async def get_connections(self) -> List[DatabaseConnection]:
        """Get all stored database connections"""
        return self.db.query(DatabaseConnection).all()

    async def get_connection(self, connection_id: int) -> Optional[DatabaseConnection]:
        """Get a specific database connection by ID"""
        return self.db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()

    async def delete_connection(self, connection_id: int) -> bool:
        """Delete a database connection"""
        connection = await self.get_connection(connection_id)
        if connection:
            self.db.delete(connection)
            await self.db.commit()
            return True
        return False

    async def test_connection(self, connection_id: int) -> bool:
        """Test if a database connection is still valid"""
        connection = await self.get_connection(connection_id)
        if not connection:
            return False

        try:
            if connection.engine == "sqlite":
                conn_str = f"sqlite:///{connection.database}"
            elif connection.engine == "postgresql":
                conn_str = f"postgresql://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
            else:  # MySQL
                conn_str = f"mysql+mysqlconnector://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"

            engine = create_engine(conn_str)
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False 