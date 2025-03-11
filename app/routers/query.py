from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.query import QueryService
from app.models.connection import Connection
from app.models.database import QueryHistory
from app.schemas.query import QueryRequest, QueryResponse, QueryHistoryResponse
from typing import List, Optional
from app.core.auth import get_current_user
from fastapi.templating import Jinja2Templates
import mysql.connector
import time
from datetime import datetime
from app.services.nl_to_sql_service import NLToSQLService
import logging
from app.core.config import settings
from app.core.dependencies import get_templates

# Configure logging
logger = logging.getLogger(__name__)

# Create separate routers for web and API
web_router = APIRouter(prefix="/query", tags=["query-web"])
api_router = APIRouter(prefix="/api/query", tags=["query-api"])

def execute_sql_query(sql_query: str) -> dict:
    """Execute SQL query and return results with execution time"""
    start_time = time.time()
    try:
        # TODO: Use connection pooling instead of creating new connections
        connection = mysql.connector.connect(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        cursor.close()
        connection.close()
        
        execution_time = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "success",
            "columns": columns,
            "results": results,
            "execution_time": execution_time,
            "error": None
        }
    except mysql.connector.Error as e:
        logger.error(f"Database error: {str(e)}")
        execution_time = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "error",
            "columns": [],
            "results": [],
            "execution_time": execution_time,
            "error": f"Database error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        execution_time = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "error",
            "columns": [],
            "results": [],
            "execution_time": execution_time,
            "error": f"Unexpected error: {str(e)}"
        }

@web_router.get("/")
async def show_query_form(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    """Show the query input form"""
    return templates.TemplateResponse(
        "query_form.html",
        {"request": request}
    )

@web_router.post("/")
async def process_query(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    """Process natural language query and show results"""
    try:
        form_data = await request.form()
        natural_query = form_data.get("query")
        
        if not natural_query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        nl_service = NLToSQLService()
        
        schema_info = """
        Table: users
        Columns:
        - id (int, primary key, auto_increment)
        - email (varchar(255), unique, not null)
        - first_name (varchar(100))
        - last_name (varchar(100))
        - created_at (datetime)
        - updated_at (datetime)

        Table: query_history
        Columns:
        - id (int, primary key, auto_increment)
        - user_id (int, foreign key references users.id)
        - natural_query (text, not null)
        - sql_query (text, not null)
        - execution_time (float)
        - status (varchar(50))
        - error_message (text)
        - created_at (datetime)
        """
        
        result = nl_service.generate_sql(natural_query, schema_info)
        
        if not result["success"]:
            logger.error(f"SQL generation failed: {result['error']}")
            return templates.TemplateResponse(
                "query_result.html",
                {
                    "request": request,
                    "natural_query": natural_query,
                    "sql_query": "",
                    "status": "error",
                    "error": result["error"],
                    "execution_time": 0,
                    "columns": [],
                    "results": []
                }
            )
        
        query_result = execute_sql_query(result["sql"])
        
        if query_result["status"] == "success":
            for row in query_result["results"]:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.strftime("%Y-%m-%d %H:%M:%S")
        
        return templates.TemplateResponse(
            "query_result.html",
            {
                "request": request,
                "natural_query": natural_query,
                "sql_query": result["sql"],
                "status": query_result["status"],
                "error": query_result["error"],
                "execution_time": query_result["execution_time"],
                "columns": query_result["columns"],
                "results": query_result["results"]
            }
        )
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return templates.TemplateResponse(
            "query_result.html",
            {
                "request": request,
                "natural_query": natural_query if 'natural_query' in locals() else "",
                "sql_query": "",
                "status": "error",
                "error": f"Internal server error: {str(e)}",
                "execution_time": 0,
                "columns": [],
                "results": []
            }
        )

# API routes
@api_router.post("/{connection_id}", response_model=QueryResponse)
async def execute_query(
    connection_id: int,
    query_request: QueryRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Execute a natural language query on a database connection"""
    try:
        query_service = QueryService(db)
        result = await query_service.process_natural_language_query(
            connection_id=connection_id,
            user_id=current_user.id,
            query=query_request.query
        )
        return result
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/{connection_id}/history", response_model=QueryHistoryResponse)
async def get_query_history(
    connection_id: int,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get query history for a database connection"""
    try:
        query_service = QueryService(db)
        return query_service.get_query_history(
            connection_id=connection_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error getting query history: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 