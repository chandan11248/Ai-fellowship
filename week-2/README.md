# Week 2 Task - REST API with PostgreSQL & FastAPI

## Task Description

This project implements a complete REST API for a classic model car business database using PostgreSQL, Docker, and FastAPI.

---

## What I Learned

### Task 1: Docker & PostgreSQL Setup
- **Docker Compose**: Setting up multi-container applications
- **Environment Variables**: Using `.env` files for configuration (12-Factor App - Factor III: Config)
- **Database Initialization**: Auto-execution of SQL scripts using `/docker-entrypoint-initdb.d/`
- **12-Factor App Principles**:
  - **Factor III (Config)**: Store config in environment, not in code
  - **Factor IV (Backing Services)**: Treat database as an attached resource
  - **Factor X (Dev/Prod Parity)**: Docker makes development and production similar

### Task 2: FastAPI & Layered Architecture
- **FastAPI Framework**: Modern Python web framework with automatic documentation (Swagger UI)
- **Layered Architecture**: Clean separation of concerns
  - **Router Layer** (`router.py`): Handles HTTP requests/responses
  - **CRUD Layer** (`crud.py`): Business logic and database operations
  - **Schema Layer** (`schemas.py`): Data validation using Pydantic
  - **Database Layer** (`database.py`): SQLAlchemy ORM models
- **SQLAlchemy ORM**: Object-Relational Mapping for database operations
- **Pydantic**: Data validation using Python type annotations
- **Logging**: Implemented logging across all layers

### Task 3: Modularity & Concurrency
- **Modularity**: Created 8 separate count endpoints for each table
- **Concurrency**: Implemented `/overall_counts` endpoint that fetches counts from all 8 tables efficiently
- **Factor VIII (Concurrency)**: Understanding synchronous execution for database queries

---

## API Endpoints Implemented

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/customers` | GET | List customers with pagination (skip/limit) |
| `/customers/{id}` | GET | Get single customer with orders and payments |
| `/customers/count` | GET | Total customers count |
| `/orders/count` | GET | Total orders count |
| `/products/count` | GET | Total products count |
| `/employees/count` | GET | Total employees count |
| `/offices/count` | GET | Total offices count |
| `/payments/count` | GET | Total payments count |
| `/orderdetails/count` | GET | Total order details count |
| `/productlines/count` | GET | Total product lines count |
| `/overall_counts` | GET | Concurrent count from all 8 tables |

---

## Project Structure

```
week-2/
├── .env                 # Environment variables (database config)
├── docker-compose.yml  # Docker PostgreSQL setup
├── requirements.txt     # Python dependencies
├── main.py             # FastAPI application entry point
├── config.py           # Configuration management
├── database.py          # SQLAlchemy ORM models
├── schemas.py          # Pydantic models for validation
├── crud.py             # CRUD operations
├── router.py           # API endpoints
├── logging_setup.py    # Logging configuration
├── seed.sql            # Database initialization data
└── Task1_Week2.pdf     # Task description
├── Task2_Week2.pdf     # Task description
└── Task3_Week2.pdf     # Task description
```

---

## How to Run

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11+

### Steps

1. **Start PostgreSQL**:
   ```bash
   cd week-2
   docker-compose up -d
   ```

2. **Install Python dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the API**:
   ```bash
   python main.py
   # OR
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

4. **Access API Documentation**:
   - Swagger UI: http://localhost:8000/docs

---

## Database Tables

The database contains 8 tables with sample data:
1. `customers` - Customer information (122 records)
2. `orders` - Customer orders (326 records)
3. `products` - Product catalog (110 records)
4. `employees` - Employee data (23 records)
5. `offices` - Office locations (7 records)
6. `payments` - Payment records (273 records)
7. `orderdetails` - Order line items (2996 records)
8. `productlines` - Product categories (7 records)

---

## Key Technical Concepts Learned

1. **12-Factor App Methodology**: Principles for building scalable SaaS applications
2. **RESTful API Design**: Proper endpoint design with pagination
3. **SQLAlchemy ORM**: Database abstraction layer
4. **Pydantic Validation**: Data validation using Python type hints
5. **Docker Containerization**: Consistent environments across development and production
6. **Layered Architecture**: Separation of concerns in API design
7. **Logging**: Application monitoring and debugging

---

## Technology Stack

- **Database**: PostgreSQL (via Docker)
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Validation**: Pydantic
- **Server**: Uvicorn
- **Container**: Docker Compose

---

*This task was completed as part of the AI Fellowship Week 2 assignment.*