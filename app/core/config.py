from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
import secrets

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI SQL Chatbot"
    
    # Security
    SECRET_KEY: str = secrets.token_hex(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Hugging Face
    HUGGINGFACE_API_KEY: Optional[str] = None
    HUGGINGFACE_MODEL: str = "bigcode/starcoder"  # Default model
    
    # Database
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "ai_sql_chatbot"
    
    @property
    def MYSQL_URL(self) -> str:
        """Generate MySQL connection URL"""
        return f"mysql+mysqlconnector://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    # Connection Pool Settings
    MAX_CONNECTIONS_COUNT: int = 10
    MIN_CONNECTIONS_COUNT: int = 1

    class Config:
        env_file = ".env"
        case_sensitive = True

    def check_huggingface_api_key(self):
        if not self.HUGGINGFACE_API_KEY:
            raise ValueError(
                "Hugging Face API key not found. Please set the HUGGINGFACE_API_KEY environment variable "
                "in your .env file or system environment variables."
            )

@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    return settings

settings = get_settings() 