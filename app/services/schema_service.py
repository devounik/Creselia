from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class SchemaService:
    def __init__(self, connection_url: str, db_type: str, database_name: str):
        """Initialize SchemaService with database connection details"""
        logger.info(f"Initializing SchemaService for {database_name}")
        
        # Create engine with proper settings
        self.engine = create_engine(
            connection_url,
            pool_pre_ping=True,  # Enable connection health checks
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=False           # Disable SQL logging
        )
        self.db_type = db_type.lower()
        self.database_name = database_name

    def get_relationships(self) -> List[Dict]:
        """Get foreign key relationships based on database type"""
        if self.db_type == "mysql":
            query = text("""
                SELECT 
                    TABLE_NAME AS child_table,
                    COLUMN_NAME AS child_column,
                    REFERENCED_TABLE_NAME AS parent_table,
                    REFERENCED_COLUMN_NAME AS parent_column
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = :db_name
                    AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
        else:
            raise ValueError(f"Database type {self.db_type} not supported yet")

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"db_name": self.database_name})
                relationships = [
                    {
                        "child_table": row.child_table,
                        "child_column": row.child_column,
                        "parent_table": row.parent_table,
                        "parent_column": row.parent_column
                    }
                    for row in result
                ]
                logger.info(f"Found {len(relationships)} relationships")
                return relationships
        except Exception as e:
            logger.error(f"Error getting relationships: {str(e)}")
            raise ValueError(f"Failed to get relationships: {str(e)}")

    def get_schema_info(self) -> List[Dict]:
        """Get detailed schema information based on database type"""
        if self.db_type == "mysql":
            query = text("""
                SELECT 
                    TABLE_NAME, 
                    COLUMN_NAME, 
                    DATA_TYPE, 
                    COLUMN_TYPE, 
                    IS_NULLABLE, 
                    COLUMN_KEY, 
                    EXTRA
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = :db_name
            """)
        else:
            raise ValueError(f"Database type {self.db_type} not supported yet")

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"db_name": self.database_name})
                schema_info = [
                    {
                        "TABLE_NAME": row.TABLE_NAME,
                        "COLUMN_NAME": row.COLUMN_NAME,
                        "DATA_TYPE": row.DATA_TYPE,
                        "COLUMN_TYPE": row.COLUMN_TYPE,
                        "IS_NULLABLE": row.IS_NULLABLE,
                        "COLUMN_KEY": row.COLUMN_KEY,
                        "EXTRA": row.EXTRA
                    }
                    for row in result
                ]
                logger.info(f"Found {len(schema_info)} columns across all tables")
                return schema_info
        except Exception as e:
            logger.error(f"Error getting schema info: {str(e)}")
            raise ValueError(f"Failed to get schema info: {str(e)}")

    def format_schema_for_prompt(self) -> str:
        """Format schema and relationships for the LLM prompt"""
        try:
            schema_info = self.get_schema_info()
            relationships = self.get_relationships()

            # Format table and column information
            tables = {}
            for col in schema_info:
                table_name = col["TABLE_NAME"]
                if table_name not in tables:
                    tables[table_name] = []
                tables[table_name].append({
                    "name": col["COLUMN_NAME"],
                    "type": col["DATA_TYPE"],
                    "nullable": col["IS_NULLABLE"],
                    "key": col["COLUMN_KEY"],
                    "extra": col["EXTRA"]
                })

            logger.info(f"Formatting schema for {len(tables)} tables")

            # Format the schema string
            schema_str = "Database Schema:\n\n"
            for table, columns in tables.items():
                schema_str += f"Table: {table}\n"
                for col in columns:
                    schema_str += f"  - {col['name']} ({col['type']})"
                    if col['key'] == 'PRI':
                        schema_str += " PRIMARY KEY"
                    if not col['nullable'] == 'YES':
                        schema_str += " NOT NULL"
                    schema_str += "\n"
                schema_str += "\n"

            # Add relationships
            if relationships:
                schema_str += "Relationships:\n"
                for rel in relationships:
                    schema_str += f"  - {rel['child_table']}.{rel['child_column']} -> {rel['parent_table']}.{rel['parent_column']}\n"

            return schema_str
        except Exception as e:
            logger.error(f"Error formatting schema: {str(e)}")
            raise 