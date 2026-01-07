# User Registration App

A FastAPI-based user registration application with PostgreSQL database, Redis caching, and Kafka messaging.

## Tech Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL 16.11
- **Cache**: Redis 8.0.5
- **Message Queue**: Apache Kafka
- **ORM**: SQLAlchemy
- **Database Admin**: pgAdmin 4

## Features

- User registration system
- Email verification with OTP
- Password hashing
- RESTful API endpoints

## Project Structure

```
intern_proj/
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── requirements.txt     # Python dependencies
│   └── src/
│       ├── api/             # API routes
│       ├── models/          # Database and API models
│       ├── utils/           # Utility functions (hasher, OTP, email)
│       └── session.py       # Database session management
├── docker-compose.yaml      # Docker services configuration
└── README.md
```

## Prerequisites

- Python 3.8+
- Docker and Docker Compose

## Getting Started

### 1. Start Docker Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- pgAdmin on port 5050
- Redis on port 6379
- Kafka

### 2. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python -m uvicorn main:app --reload --host localhost --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Database Access

**pgAdmin**: http://localhost:5050

**PostgreSQL Connection**:
- Host: localhost
- Port: 5432

## Development

The application uses:
- **Pydantic** for data validation
- **SQLAlchemy** for ORM
- **Uvicorn** as ASGI server
