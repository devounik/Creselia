from typing import Dict, Any, Optional
import aiohttp
from app.core.config import settings
import re
import logging
from sqlalchemy import text
from fastapi import HTTPException
import sqlparse

logger = logging.getLogger(__name__)

class NLToSQLService:
    def __init__(self):
        self.api_url = f"https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        self.headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
        self.model_params = {
            "max_new_tokens": 256,
            "temperature": 0.1,
            "top_p": 0.95,
            "do_sample": True,
            "return_full_text": False
        }
        
        self.dangerous_keywords = {
            'DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE',
            'RENAME', 'REPLACE', 'PROCEDURE', 'FUNCTION', 'TRIGGER', 'GRANT',
            'REVOKE', 'ROLE', 'INTO', 'OUTFILE', 'DUMPFILE', 'LOAD_FILE'
        }
        
        self.allowed_functions = {
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'ROUND', 'FLOOR', 'CEILING',
            'CONCAT', 'SUBSTRING', 'TRIM', 'UPPER', 'LOWER', 'DATE', 'YEAR',
            'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND'
        }
    
    def create_prompt(self, question: str, schema_info: str) -> str:
        """Create a detailed prompt for Mistral model"""
        return f"""<s>[INST] You are an expert SQL developer. Convert the following natural language question into a SQL query based on the given database schema.

Database Schema:
{schema_info}

Instructions:
1. Generate ONLY SELECT queries (no INSERT, UPDATE, DELETE, etc.)
2. Follow these SQL best practices:
   - Use meaningful table aliases (e.g., 'members m' not just 'm')
   - Always qualify column names with table aliases (e.g., 'm.member_id')
   - Use proper JOIN syntax with ON conditions (e.g., 'JOIN other_table o ON o.id = m.other_id')
   - Handle NULL values appropriately
   - Use WHERE clauses for filtering
   - Use GROUP BY for aggregations
   - Use HAVING for filtering aggregated results
   - Use ORDER BY for sorting when relevant
3. When joining tables:
   - Always include the table in the FROM clause before referencing it
   - Properly specify JOIN conditions
   - Do not reference tables that haven't been joined
4. Return ONLY the SQL query without any explanation or comments

Question: {question}

Generate a SQL query that answers this question. Return ONLY the SQL query, nothing else. [/INST]</s>"""

    async def validate_sql(self, query: str) -> bool:
        """Validate SQL query for safety"""
        try:
            # Parse the SQL query
            parsed = sqlparse.parse(query)
            if not parsed:
                return False
                
            # Get the first statement
            stmt = parsed[0]
            
            # Check if it's a SELECT statement
            if stmt.get_type() != 'SELECT':
                logger.warning(f"Query type {stmt.get_type()} not allowed")
                return False
            
            # Convert to uppercase for keyword checking
            query_upper = query.upper()
            
            # Check for dangerous keywords
            for keyword in self.dangerous_keywords:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, query_upper):
                    logger.warning(f"Dangerous keyword found: {keyword}")
                    return False
            
            # Check for comments
            if '--' in query or '/*' in query:
                logger.warning("Comments not allowed in query")
                return False
            
            # Check for multiple statements
            if ';' in query[:-1]:  # Allow semicolon at the end
                logger.warning("Multiple statements not allowed")
                return False
            
            # Validate functions used
            for token in stmt.tokens:
                if token.ttype is sqlparse.tokens.Name:
                    func_name = token.value.upper()
                    if (
                        func_name.endswith('(') 
                        and func_name[:-1] not in self.allowed_functions
                    ):
                        logger.warning(f"Function not allowed: {func_name}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating SQL query: {str(e)}")
            return False

    def _clean_sql_query(self, query: str) -> str:
        """Clean and format SQL query"""
        try:
            if not query:
                raise ValueError("Empty query")
            
            # Remove markdown code block syntax
            query = re.sub(r'```sql\s*|\s*```', '', query)
            
            # Remove numbered points and explanations
            query = re.sub(r'^\d+\.\s*', '', query)
            query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
            
            # Fix common SQL keyword abbreviations
            replacements = {
                r'\bSEL\b': 'SELECT',
                r'\bFR\b': 'FROM',
                r'\bWH\b': 'WHERE',
                r'\bGR\b': 'GROUP BY',
                r'\bORD\b': 'ORDER BY',
                r'\bHAV\b': 'HAVING',
                r'\bJOI\b': 'JOIN',
                r'\bLJ\b': 'LEFT JOIN',
                r'\bRJ\b': 'RIGHT JOIN',
                r'\bIJ\b': 'INNER JOIN',
                r'\bDIST\b': 'DISTINCT'
            }
            
            for pattern, replacement in replacements.items():
                query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
            
            # Ensure it starts with SELECT
            if not query.strip().upper().startswith('SELECT'):
                query = 'SELECT ' + query
            
            # Format the query using sqlparse
            query = sqlparse.format(
                query,
                keyword_case='upper',
                identifier_case='lower',
                strip_comments=True,
                reindent=True
            )
            
            # Remove extra whitespace and ensure single spaces
            query = ' '.join(query.split())
            
            # Ensure the query ends with a semicolon
            if not query.strip().endswith(';'):
                query += ';'
            
            return query
            
        except Exception as e:
            logger.error(f"Error cleaning SQL query: {str(e)}")
            raise ValueError(f"Failed to clean SQL query: {str(e)}")

    async def generate_sql(self, natural_query: str, schema: str) -> Dict[str, Any]:
        """Generate SQL from natural language query"""
        try:
            # Generate SQL using AI model
            sql_query = await self._generate_raw_sql(natural_query, schema)
            
            # Clean and format the query
            cleaned_query = self._clean_sql_query(sql_query)
            
            # Validate the query
            if not await self.validate_sql(cleaned_query):
                raise ValueError("Generated query failed security validation")
            
            # Try to parse the query to catch syntax errors
            try:
                parsed = sqlparse.parse(cleaned_query)[0]
                if not parsed.tokens:
                    raise ValueError("Failed to parse generated SQL")
            except Exception as e:
                logger.error(f"SQL parsing error: {str(e)}")
                raise ValueError("Generated SQL is not valid")
            
            return {
                "success": True,
                "sql": cleaned_query,
                "explanation": f"Generated SQL query: {cleaned_query}"
            }
            
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _generate_raw_sql(self, natural_query: str, schema: str) -> str:
        """Generate raw SQL using AI model"""
        try:
            print("\nGenerating SQL for question:", natural_query)
            print("\nUsing schema:")
            print("-" * 50)
            print(schema)
            print("-" * 50)
            
            prompt = self.create_prompt(natural_query, schema)
            print("\nGenerated prompt:")
            print("-" * 50)
            print(prompt)
            print("-" * 50)
            
            # Make API call to Hugging Face using aiohttp
            print("\nMaking API call to Hugging Face...")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "inputs": prompt,
                        "parameters": self.model_params
                    }
                ) as response:
                    if response.status != 200:
                        error_msg = f"API request failed with status {response.status}: {await response.text()}"
                        print("\nError:", error_msg)
                        return ""

                    # Extract and clean SQL from response
                    print("\nGot response from API, extracting SQL...")
                    response_json = await response.json()
                    generated_text = response_json[0]["generated_text"]
                    print("\nRaw generated text:")
                    print("-" * 50)
                    print(generated_text)
                    print("-" * 50)
                    
                    return generated_text

        except Exception as e:
            import traceback
            error_msg = f"Failed to generate SQL: {str(e)}\n{traceback.format_exc()}"
            print("\nError:", error_msg)
            return ""

    def _generate_query_explanation(self, query: str) -> str:
        """Generate a natural language explanation of the SQL query"""
        parts = []
        query_lower = query.lower()
        
        # Analyze SELECT clause
        if "distinct" in query_lower:
            parts.append("retrieving unique records")
        
        # Analyze JOINs
        if "join" in query_lower:
            join_count = query_lower.count("join")
            parts.append(f"combining data from {join_count + 1} tables")
        
        # Analyze WHERE clause
        if "where" in query_lower:
            parts.append("filtering results based on specified conditions")
        
        # Analyze GROUP BY
        if "group by" in query_lower:
            parts.append("grouping results")
            if "having" in query_lower:
                parts.append("applying filters to grouped data")
        
        # Analyze ORDER BY
        if "order by" in query_lower:
            if "desc" in query_lower:
                parts.append("sorting results in descending order")
            else:
                parts.append("sorting results in ascending order")
        
        # Analyze aggregations
        agg_functions = ["count(", "sum(", "avg(", "max(", "min("]
        if any(func in query_lower for func in agg_functions):
            parts.append("calculating aggregate values")
        
        explanation = " and ".join(parts)
        return f"This query is {explanation}." 