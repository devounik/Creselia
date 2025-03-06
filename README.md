# AI-Powered Natural Language to SQL Chatbot

A web-based chat application that converts natural language queries to SQL using AI (Hugging Face), allowing users to interact with their databases using plain English.

## Features

- 🔐 Database Connection Setup (MySQL, PostgreSQL, SQLite)
- 🤖 Natural Language to SQL Conversion using AI (Hugging Face)
- 🛡️ Secure Query Execution (Read-only)
- ⚡ AI Query Optimization
- 🔍 Error Handling & Feedback
- 💻 User-Friendly Bootstrap Interface
- 🔄 Multi-Database Support

## Tech Stack

- **Frontend**: HTML, CSS, Bootstrap
- **Backend**: FastAPI (Python)
- **AI**: Hugging Face Inference API
- **Database**: 
  - Application DB: MySQL
  - Supported User DBs: MySQL, PostgreSQL, SQLite
- **ORM**: SQLAlchemy

## Prerequisites

- Python 3.8+
- MySQL Server
- Hugging Face API Key

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd sql-chatbot
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a .env file with the following content:
```env
# Security
SECRET_KEY=your-secret-key

# Hugging Face Settings
HUGGINGFACE_API_KEY=your-huggingface-api-key
HUGGINGFACE_MODEL=bigcode/starcoder

# MySQL Database Settings
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your-mysql-user
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=your-database-name

# API Settings
API_V1_STR=/api/v1
PROJECT_NAME=AI SQL Chatbot
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

## Project Structure

```
app/
├── core/           # Core functionality
│   ├── config.py   # Configuration settings
│   └── database.py # Database connection
├── models/         # SQLAlchemy models
├── routers/        # API routes
├── schemas/        # Pydantic models
├── services/       # Business logic
├── static/         # Static files
└── templates/      # HTML templates
```

## API Endpoints

- `POST /api/connect`: Connect to a database
- `POST /api/query`: Convert English to SQL and execute
- `GET /api/schema/{connection_id}`: Get database schema

## Security Features

- Read-only queries (SELECT only)
- SQL injection prevention
- Parameterized queries
- Input validation
- Error handling

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/)
- [Hugging Face](https://huggingface.co/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Bootstrap](https://getbootstrap.com/) 