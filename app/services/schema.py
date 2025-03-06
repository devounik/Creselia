from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from app.models.database import DatabaseConnection
from typing import Dict, Any, Optional

class SchemaService:
    def __init__(self, db: Session):
        self.db = db

    async def get_schema(self, connection_id: int) -> Optional[Dict[str, Any]]:
        """Get the schema for a specific database connection"""
        connection = self.db.query(DatabaseConnection)\
            .filter(DatabaseConnection.id == connection_id)\
            .first()
        
        if not connection:
            return None
        
        return connection.schema

    async def refresh_schema(self, connection_id: int) -> Dict[str, Any]:
        """Refresh the schema for a specific database connection"""
        connection = self.db.query(DatabaseConnection)\
            .filter(DatabaseConnection.id == connection_id)\
            .first()
        
        if not connection:
            raise ValueError("Connection not found")

        try:
            # Create connection string
            if connection.engine == "sqlite":
                conn_str = f"sqlite:///{connection.database}"
            elif connection.engine == "postgresql":
                conn_str = f"postgresql://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
            else:  # MySQL
                conn_str = f"mysql+mysqlconnector://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"

            # Get schema
            engine = create_engine(conn_str)
            with engine.connect() as conn:
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
                
                result = conn.execute(text(schema_query))
                schema = [dict(row) for row in result]

            # Update connection schema
            connection.schema = schema
            self.db.add(connection)
            await self.db.commit()

            return schema

        except Exception as e:
            raise Exception(f"Failed to refresh schema: {str(e)}")

    async def get_table_info(self, connection_id: int, table_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific table"""
        schema = await self.get_schema(connection_id)
        if not schema:
            raise ValueError("Schema not found")

        table_info = {
            "name": table_name,
            "columns": []
        }

        for item in schema:
            if item["table_name"].lower() == table_name.lower():
                table_info["columns"].append({
                    "name": item["column_name"],
                    "type": item["data_type"]
                })

        if not table_info["columns"]:
            raise ValueError(f"Table {table_name} not found in schema")

        return table_info 