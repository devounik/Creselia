from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import database, query, schema, auth, connections, dashboard, chat
from app.core.config import settings
from app.core.database import init_db
from app.core.middleware import AuthMiddleware
from app.core.dependencies import get_templates, templates
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configure SQLAlchemy logging
sqlalchemy_loggers = [
    'sqlalchemy.engine',
    'sqlalchemy.pool',
    'sqlalchemy.dialects',
    'sqlalchemy.orm'
]

for logger_name in sqlalchemy_loggers:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.ERROR)
    logger.propagate = False

# Set uvicorn access logs to WARNING to reduce noise
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
logging.getLogger('uvicorn.error').setLevel(logging.WARNING)

# Keep our application logging at INFO level
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI SQL Chatbot",
    description="Natural Language to SQL Query Converter",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware
app.add_middleware(AuthMiddleware)

# Create static directory structure
static_dirs = ["css", "js", "images"]
for dir_name in static_dirs:
    os.makedirs(f"app/static/{dir_name}", exist_ok=True)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize database
logger.info("Initializing database...")
init_db()
logger.info("Database initialized successfully!")

# Include routers
app.include_router(auth.web_router)  # Web routes at root
app.include_router(auth.api_router)  # API routes at /api/auth
app.include_router(dashboard.router)  # Dashboard routes
app.include_router(connections.router)  # Connection management routes
app.include_router(query.web_router)  # Query web interface at /query
app.include_router(query.api_router)  # Query API at /api/query
app.include_router(schema.router, prefix="/api", tags=["schema"])  # Schema API
app.include_router(chat.router)  # Chat interface

# Root route
@app.get("/")
async def root(request: Request):
    """Render the home page"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    ) 