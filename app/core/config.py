from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache
import secrets

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI SQL Chatbot"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SECURE_COOKIES: bool = False  # Set to True in production
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # Hugging Face
    HUGGINGFACE_API_KEY: str
    HUGGINGFACE_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.2"  # Using Mistral for SQL generation
    
    # MySQL Database Settings
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456789"
    MYSQL_DATABASE: str = "collegeproject"
    
    @property
    def MYSQL_URL(self) -> str:
        """Generate MySQL connection URL with explicit charset and connection settings"""
        return f"mysql+mysqlconnector://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
    
    # Connection Pool Settings
    MAX_CONNECTIONS_COUNT: int = 10
    MIN_CONNECTIONS_COUNT: int = 1
    
    # JWT settings
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)  # Generate a secure secret key
    JWT_ALGORITHM: str = "HS256"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def check_huggingface_api_key(self):
        if not self.HUGGINGFACE_API_KEY:
            raise ValueError(
                "Hugging Face API key not found. Please set the HUGGINGFACE_API_KEY environment variable "
                "in your .env file or system environment variables."
            )

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings() 