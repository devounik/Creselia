from app.services.nl_to_sql_service import NLToSQLService
import mysql.connector
from datetime import datetime

def execute_sql_query(sql_query: str) -> tuple:
    """Execute SQL query and return results"""
    try:
        # Create database connection
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="123456789",
            database="collegeproject"
        )
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        # Get column names
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        cursor.close()
        connection.close()
        
        return columns, results
    except Exception as e:
        return [], {"error": str(e)}

def test_nl_to_sql():
    # Initialize the service
    nl_service = NLToSQLService()
    
    # Sample schema info
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
    
    # Test query
    test_question = "Show me all users who joined in the last 7 days"
    
    # Generate SQL
    result = nl_service.generate_sql(test_question, schema_info)
    
    # Print results
    print("\nTest Results:")
    print("-" * 50)
    print(f"Question: {test_question}")
    print("-" * 50)
    if result["success"]:
        print("Generated SQL:")
        print(result["sql"])
        print("\nExplanation:")
        print(result["explanation"])
        
        # Execute the query and get results
        print("\nQuery Results:")
        print("-" * 50)
        columns, query_results = execute_sql_query(result["sql"])
        
        if isinstance(query_results, dict) and "error" in query_results:
            print(f"Error executing query: {query_results['error']}")
        else:
            # Print column headers
            if columns:
                print(" | ".join(columns))
                print("-" * (len(" | ".join(columns))))
            
            # Print results
            if query_results:
                for row in query_results:
                    # Format datetime objects and handle None values
                    formatted_row = []
                    for col in columns:
                        value = row[col]
                        if isinstance(value, datetime):
                            formatted_row.append(value.strftime("%Y-%m-%d %H:%M:%S"))
                        elif value is None:
                            formatted_row.append("NULL")
                        else:
                            formatted_row.append(str(value))
                    print(" | ".join(formatted_row))
            else:
                print("No results found")
    else:
        print("Error:")
        print(result["error"])

if __name__ == "__main__":
    test_nl_to_sql() 