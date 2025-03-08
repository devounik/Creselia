from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from app.models.connection import Connection
from app.services.database import DatabaseService
from typing import Dict, Any, List, Optional

class SchemaService:
    def __init__(self, db: Session):
        self.db = db
        self.database_service = DatabaseService(db)

    def get_schema(self, connection_id: int, user_id: int) -> Dict[str, Any]:
        """Get the schema for a database connection"""
        # Get the connection and verify ownership
        connection = self.database_service.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        # Get schema from connection or fetch it
        schema = connection.schema
        if not schema:
            schema = self.database_service.get_schema(connection)
            connection.schema = schema
            self.db.commit()

        return schema

    def get_tables(self, connection_id: int, user_id: int) -> List[str]:
        """Get list of tables in the database"""
        schema = self.get_schema(connection_id, user_id)
        return list(schema.keys())

    def get_table_columns(self, connection_id: int, table_name: str, user_id: int) -> List[Dict[str, Any]]:
        """Get column information for a specific table"""
        schema = self.get_schema(connection_id, user_id)
        if table_name not in schema:
            raise ValueError(f"Table {table_name} not found in schema")
        return schema[table_name]["columns"]

    def refresh_schema(self, connection_id: int, user_id: int) -> Dict[str, Any]:
        """Force refresh the schema for a database connection"""
        # Get the connection and verify ownership
        connection = self.database_service.get_connection(connection_id, user_id)
        if not connection:
            raise ValueError("Connection not found")

        # Fetch fresh schema
        schema = self.database_service.get_schema(connection)
        connection.schema = schema
        self.db.commit()

        return schema

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