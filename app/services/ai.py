from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.core.config import settings
from fastapi import HTTPException
import requests
import json

class SQLQuery(BaseModel):
    query: str = Field(description="The generated SQL query")
    explanation: str = Field(description="Explanation of what the query does")

class AIService:
    def __init__(self):
        if not settings.HUGGINGFACE_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Hugging Face API key not configured. Please set HUGGINGFACE_API_KEY in your environment variables."
            )
        
        self.api_url = f"https://api-inference.huggingface.co/models/{settings.HUGGINGFACE_MODEL}"
        self.headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}

    async def natural_to_sql(self, natural_query: str, schema: Dict[str, Any]) -> str:
        """Convert natural language query to SQL using AI"""
        try:
            # Create a schema description for the AI
            schema_description = self._format_schema_description(schema)
            
            # Create the prompt
            prompt = f"""You are an expert SQL query generator. Convert the following natural language question into a SQL query.
            
            Rules:
            1. Only generate SELECT queries (no INSERT, UPDATE, DELETE)
            2. Use proper SQL syntax
            3. Include appropriate JOINs when needed
            4. Add WHERE clauses to filter data appropriately
            5. Use proper column names from the schema
            6. Optimize the query for performance
            
            Database Schema:
            {schema_description}
            
            Question: {natural_query}
            
            Generate only the SQL query, without any explanation or additional text."""
            
            # Make request to Hugging Face API
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"inputs": prompt, "parameters": {"max_length": 500}}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to get response from Hugging Face API"
                )

            # Extract SQL query from response
            sql_query = response.json()[0]["generated_text"].strip()
            
            # Validate the SQL query (basic checks)
            if not sql_query.upper().startswith("SELECT"):
                raise ValueError("Only SELECT queries are allowed")
            
            # Validate SQL query
            if not await self.validate_sql(sql_query):
                raise ValueError("Generated query contains unsafe operations")
            
            return sql_query

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to generate SQL query: {str(e)}"
            )

    def _format_schema_description(self, schema: Dict[str, Any]) -> str:
        """Format the database schema into a readable string for the AI"""
        description = []
        
        # Group by table
        tables = {}
        for table_info in schema:
            table_name = table_info["table_name"]
            if table_name not in tables:
                tables[table_name] = []
            tables[table_name].append(f"{table_info['column_name']} ({table_info['data_type']})")
        
        # Format each table
        for table_name, columns in tables.items():
            description.append(f"Table: {table_name}")
            description.append("Columns:")
            for column in columns:
                description.append(f"  - {column}")
            description.append("")
        
        return "\n".join(description)

    async def validate_sql(self, sql_query: str) -> bool:
        """Validate that the SQL query is safe to execute"""
        # Convert to uppercase for easier checking
        upper_query = sql_query.upper()
        
        # Check if it's a SELECT query
        if not upper_query.strip().startswith("SELECT"):
            return False
        
        # Check for dangerous keywords
        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER"]
        if any(keyword in upper_query for keyword in dangerous_keywords):
            return False
        
        return True 