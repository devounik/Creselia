from typing import Optional, Any
import mysql.connector
from mysql.connector import Error
from app.models.connection import Connection

class QueryResult:
    def __init__(self, columns: list[str], rows: list[list[Any]]):
        self.columns = columns
        self.rows = rows

class DatabaseService:
    def __init__(self, connection: Connection):
        self.connection = connection
        self._db_connection = None
    
    async def connect(self) -> None:
        """Establish a connection to the database."""
        try:
            self._db_connection = mysql.connector.connect(
                host=self.connection.host,
                port=self.connection.port,
                database=self.connection.database,
                user=self.connection.username,
                password=self.connection.password
            )
        except Error as e:
            raise Exception(f"Error connecting to database: {str(e)}")
    
    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._db_connection and self._db_connection.is_connected():
            self._db_connection.close()
    
    async def execute_query(self, query: str) -> Optional[QueryResult]:
        """Execute a SQL query and return the results."""
        try:
            if not self._db_connection or not self._db_connection.is_connected():
                await self.connect()
            
            cursor = self._db_connection.cursor()
            cursor.execute(query)
            
            # For SELECT queries, fetch results
            if query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                cursor.close()
                return QueryResult(columns=columns, rows=rows)
            
            # For other queries (INSERT, UPDATE, DELETE), commit changes
            self._db_connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            
            # Return result with affected rows count
            return QueryResult(
                columns=['affected_rows'],
                rows=[[affected_rows]]
            )
            
        except Error as e:
            raise Exception(f"Error executing query: {str(e)}")
        finally:
            await self.disconnect()
    
    async def test_connection(self) -> bool:
        """Test if the database connection can be established."""
        try:
            await self.connect()
            return True
        except Exception:
            return False
        finally:
            await self.disconnect() 