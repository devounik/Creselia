from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.models.connection import Connection
from app.schemas.database import DatabaseConnectionCreate
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
import mysql.connector
from mysql.connector import Error as MySQLError
try:
    import psycopg2
    from psycopg2 import Error as PostgreSQLError
    from psycopg2.extras import DictCursor
except ImportError:
    psycopg2 = None
    PostgreSQLError = Exception
import sqlite3
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db: Session):
        self.db = db

    def get_connections(self, user_id: int) -> List[Connection]:
        """Get all stored database connections for a user"""
        try:
            connections = self.db.query(Connection).filter(Connection.user_id == user_id).all()
            logger.debug(f"Retrieved {len(connections)} connections for user {user_id}")
            return connections
        except Exception as e:
            logger.error(f"Error retrieving connections for user {user_id}: {e}")
            return []

    def get_connection(self, connection_id: int, user_id: int) -> Optional[Connection]:
        """Get a connection by ID and verify ownership"""
        try:
            connection = self.db.query(Connection).filter(
                Connection.id == connection_id,
                Connection.user_id == user_id
            ).first()
            if connection:
                logger.debug(f"Retrieved connection {connection_id} for user {user_id}")
            else:
                logger.warning(f"Connection {connection_id} not found for user {user_id}")
            return connection
        except Exception as e:
            logger.error(f"Error retrieving connection {connection_id} for user {user_id}: {e}")
            return None

    def test_connection(self, connection: Connection) -> bool:
        """Test if a database connection is valid"""
        conn = None
        try:
            if connection.db_type == "mysql":
                conn = mysql.connector.connect(
                    host=connection.host,
                    port=connection.port,
                    database=connection.database,
                    user=connection.username,
                    password=connection.password
                )
            elif connection.db_type == "postgresql":
                if not psycopg2:
                    raise ImportError("PostgreSQL support requires psycopg2-binary package")
                conn = psycopg2.connect(
                    host=connection.host,
                    port=connection.port,
                    dbname=connection.database,
                    user=connection.username,
                    password=connection.password
                )
            elif connection.db_type == "sqlite":
                conn = sqlite3.connect(connection.database)
            else:
                raise ValueError(f"Unsupported database type: {connection.db_type}")

            # Update last used timestamp and status
            connection.last_used = datetime.utcnow()
            connection.is_active = True
            self.db.commit()
            logger.info(f"Successfully tested connection {connection.id}")
            return True
        except (MySQLError, PostgreSQLError, sqlite3.Error) as e:
            # Update connection status
            connection.is_active = False
            self.db.commit()
            logger.error(f"Connection test failed for connection {connection.id}: {e}")
            raise Exception(f"Connection test failed: {str(e)}")
        finally:
            if conn:
                conn.close()

    def create_connection(self, connection_data: Dict[str, Any]) -> Connection:
        """Create a new database connection and store its details"""
        try:
            # Create new connection
            connection = Connection(
                name=connection_data["name"],
                description=connection_data.get("description"),
                db_type=connection_data["db_type"],
                host=connection_data.get("host"),
                port=connection_data.get("port"),
                database=connection_data["database"],
                username=connection_data.get("username"),
                password=connection_data.get("password"),
                user_id=connection_data["user_id"]
            )

            # Test the connection
            self.test_connection(connection)

            # Get the schema
            schema = self.get_schema(connection)
            connection._schema_info = json.dumps(schema)

            self.db.add(connection)
            self.db.commit()
            self.db.refresh(connection)
            logger.info(f"Successfully created connection {connection.id}")
            return connection

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create database connection: {e}")
            raise Exception(f"Failed to create database connection: {str(e)}")

    def delete_connection(self, connection_id: int, user_id: int) -> bool:
        """Delete a database connection"""
        try:
            connection = self.get_connection(connection_id, user_id)
            if connection:
                self.db.delete(connection)
                self.db.commit()
                logger.info(f"Successfully deleted connection {connection_id}")
                return True
            logger.warning(f"Connection {connection_id} not found for deletion")
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete connection {connection_id}: {e}")
            return False

    def get_schema(self, connection: Connection) -> Dict[str, Any]:
        """Get the schema of a database"""
        conn = None
        cursor = None
        try:
            schema = {}
            
            if connection.db_type == "mysql":
                conn = mysql.connector.connect(
                    host=connection.host,
                    port=connection.port,
                    database=connection.database,
                    user=connection.username,
                    password=connection.password
                )
                cursor = conn.cursor()
                
                # Get tables
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    schema[table_name] = {
                        "columns": [
                            {
                                "name": col[0],
                                "type": col[1],
                                "null": col[2],
                                "key": col[3],
                                "default": col[4],
                                "extra": col[5]
                            }
                            for col in columns
                        ]
                    }
            
            elif connection.db_type == "postgresql":
                if not psycopg2:
                    raise ImportError("PostgreSQL support requires psycopg2-binary package")
                conn = psycopg2.connect(
                    host=connection.host,
                    port=connection.port,
                    dbname=connection.database,
                    user=connection.username,
                    password=connection.password
                )
                cursor = conn.cursor()
                
                # Get tables
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"""
                        SELECT column_name, data_type, is_nullable, 
                               column_default, character_maximum_length
                        FROM information_schema.columns
                        WHERE table_name = %s
                    """, (table_name,))
                    columns = cursor.fetchall()
                    schema[table_name] = {
                        "columns": [
                            {
                                "name": col[0],
                                "type": col[1],
                                "null": col[2],
                                "default": col[3],
                                "length": col[4]
                            }
                            for col in columns
                        ]
                    }
            
            elif connection.db_type == "sqlite":
                conn = sqlite3.connect(connection.database)
                cursor = conn.cursor()
                
                # Get tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    schema[table_name] = {
                        "columns": [
                            {
                                "name": col[1],
                                "type": col[2],
                                "null": not col[3],
                                "default": col[4],
                                "primary_key": bool(col[5])
                            }
                            for col in columns
                        ]
                    }
            
            logger.info(f"Successfully retrieved schema for connection {connection.id}")
            return schema
        except (MySQLError, PostgreSQLError, sqlite3.Error) as e:
            logger.error(f"Failed to get schema for connection {connection.id}: {e}")
            raise Exception(f"Failed to get schema: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def execute_query(self, connection: Connection, query: str) -> Dict[str, Any]:
        """Execute a query on the database"""
        conn = None
        cursor = None
        try:
            if connection.db_type == "mysql":
                conn = mysql.connector.connect(
                    host=connection.host,
                    port=connection.port,
                    database=connection.database,
                    user=connection.username,
                    password=connection.password
                )
                cursor = conn.cursor(dictionary=True)
            elif connection.db_type == "postgresql":
                if not psycopg2:
                    raise ImportError("PostgreSQL support requires psycopg2-binary package")
                conn = psycopg2.connect(
                    host=connection.host,
                    port=connection.port,
                    dbname=connection.database,
                    user=connection.username,
                    password=connection.password
                )
                cursor = conn.cursor(cursor_factory=DictCursor)
            elif connection.db_type == "sqlite":
                conn = sqlite3.connect(connection.database)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
            else:
                raise ValueError(f"Unsupported database type: {connection.db_type}")

            cursor.execute(query)
            results = cursor.fetchall()

            # Convert results to list of dicts for all database types
            if connection.db_type == "sqlite":
                results = [dict(row) for row in results]
            elif connection.db_type == "postgresql":
                results = [dict(row) for row in results]

            # Update last used timestamp
            connection.last_used = datetime.utcnow()
            self.db.commit()

            logger.info(f"Successfully executed query for connection {connection.id}")
            return {
                "results": results,
                "rowCount": len(results) if results else 0
            }
        except (MySQLError, PostgreSQLError, sqlite3.Error) as e:
            logger.error(f"Query execution failed for connection {connection.id}: {e}")
            raise Exception(f"Query execution failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close() 