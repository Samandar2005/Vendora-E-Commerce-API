# Vendora E-Commerce API

Vendora is a multi-vendor e-commerce backend built with FastAPI. It provides authentication, user and store management, product and order workflows, payments, background tasks, and database migrations.

## Technology stack

- Python 3.11+
- FastAPI and Uvicorn
- PostgreSQL with SQLAlchemy and asyncpg
- Alembic for database migrations
- Redis and Celery for background tasks
- Docker Compose for local services

## Project structure

```text
app/
+-- api/           # API routers and endpoints
+-- core/          # Configuration, database, security, and exceptions
+-- models/        # SQLAlchemy models
+-- schemas/       # Pydantic schemas
+-- services/      # Business logic
+-- tasks/         # Celery tasks and worker
alembic/           # Database migrations
docker-compose.yml # Local PostgreSQL, Redis, pgAdmin, and API services
```

## Getting started

### Option 1: Docker Compose (recommended)

1. Clone the repository and enter the project directory.
2. Create the local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

3. Review `.env` and change all passwords and secret values.
4. Start the services:

   ```powershell
   docker compose up --build
   ```

The API is available at `http://localhost:8000`.

### Option 2: Run locally

1. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Start PostgreSQL and Redis, copy `.env.example` to `.env`, and update the connection settings.
4. Apply database migrations:

   ```powershell
   alembic upgrade head
   ```

5. Start the development server:

   ```powershell
   uvicorn app.main:app --reload
   ```

## API documentation

Once the server is running, interactive documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

The API includes authentication, users, stores, products, carts, orders, and payments under the versioned API routes.

## Database migrations

Create a migration after changing SQLAlchemy models:

```powershell
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Background worker

Redis is used as the Celery broker and result backend. With the Docker services running, start a worker in a separate terminal if needed:

```powershell
celery -A app.tasks.worker.celery_app worker --loglevel=info
```

## Configuration and security

Copy `.env.example` to `.env` for local development. Never commit `.env`, database credentials, JWT secrets, or other production secrets. Use strong, unique values for `SECRET_KEY` and all service passwords in production.

## License

No license has been specified yet. Add a license before distributing this project publicly.
