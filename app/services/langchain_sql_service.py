from typing import Dict, Any, Optional, List
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from app.core.config import settings

class LangChainSQLService:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0,
            model="gpt-3.5-turbo",
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.chain = self._create_chain()
    
    def _create_chain(self) -> LLMChain:
        """Create the LangChain chain with custom prompt."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a SQL expert that converts natural language questions into SQL queries.
            Given the database schema and relationships below, generate a SQL query that answers the user's question.
            
            IMPORTANT RULES:
            1. ONLY generate SELECT queries (no modifications allowed)
            2. Use proper SQL syntax and follow best practices
            3. Include helpful comments explaining the query logic
            4. Consider table relationships and use proper JOINs
            5. Format the response as a JSON-like structure with these keys:
               - sql: the generated SQL query
               - explanation: natural language explanation of what the query does
               - error: any error message (if applicable)
            
            Current Database Schema:
            {schema}
            
            Table Relationships:
            {relationships}
            """),
            ("human", "{question}")
        ])
        
        return LLMChain(
            llm=self.llm,
            prompt=prompt,
            memory=self.memory,
            verbose=True
        )
    
    async def format_schema_info(self, tables: List[Dict[str, Any]]) -> str:
        """Format table schema information for the prompt."""
        schema_text = []
        for table in tables:
            table_name = table["name"]
            columns = table["columns"]
            schema_text.append(f"Table: {table_name}")
            for col in columns:
                col_info = f"  - {col['name']} ({col['type']})"
                if col.get("key"):
                    col_info += f" {col['key']}"
                if col.get("extra"):
                    col_info += f" {col['extra']}"
                schema_text.append(col_info)
            schema_text.append("")
        return "\n".join(schema_text)
    
    async def format_relationships(self, relationships: List[Dict[str, Any]]) -> str:
        """Format table relationships for the prompt."""
        rel_text = []
        for rel in relationships:
            rel_text.append(
                f"- {rel['table1']}.{rel['column1']} -> "
                f"{rel['table2']}.{rel['column2']} ({rel['type']})"
            )
        return "\n".join(rel_text)
    
    async def generate_sql(
        self,
        question: str,
        schema_info: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate SQL from natural language question."""
        try:
            # Format schema and relationships
            schema_text = await self.format_schema_info(schema_info)
            relationships_text = await self.format_relationships(relationships)
            
            # Generate SQL using the chain
            response = await self.chain.ainvoke({
                "question": question,
                "schema": schema_text,
                "relationships": relationships_text
            })
            
            # Parse the response
            # The LLM should return a structured response we can parse
            result = response['text']
            
            # Basic error checking
            if "SELECT" not in result.upper():
                raise ValueError("Generated query is not a SELECT statement")
            
            # Extract components (you might need to adjust this based on actual response format)
            sql_part = result.split("sql:")[1].split("explanation:")[0].strip()
            explanation_part = result.split("explanation:")[1].strip()
            
            return {
                "sql": sql_part,
                "explanation": explanation_part,
                "success": True
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            } 