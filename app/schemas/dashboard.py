from pydantic import BaseModel

class UserStats(BaseModel):
    connection_count: int
    query_count: int
    # Add other fields as needed 