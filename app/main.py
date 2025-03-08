from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import database, query, schema, auth, connections, dashboard
from app.core.config import settings
from app.core.database import init_db
from app.core.middleware import AuthMiddleware
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI SQL Chatbot",
    description="Natural Language to SQL Query Converter",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware
app.add_middleware(AuthMiddleware)

# Create static directory if it doesn't exist
os.makedirs("app/static", exist_ok=True)
os.makedirs("app/static/css", exist_ok=True)
os.makedirs("app/static/js", exist_ok=True)

# Static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Initialize database
logger.info("Initializing database...")
init_db()
logger.info("Database initialized successfully!")

# Include routers
app.include_router(auth.web_router)  # Mount web routes at root
app.include_router(auth.api_router)  # Mount API routes at /api/auth
app.include_router(dashboard.router)  # Mount at root for dashboard
app.include_router(connections.router)  # Mount at root for connections
app.include_router(query.router, prefix="/api", tags=["query"])
app.include_router(schema.router, prefix="/api", tags=["schema"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 