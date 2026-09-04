# Vendora E-Commerce API

Vendora is a multi-vendor e-commerce backend built with FastAPI. It provides JWT authentication, role-based access control, seller stores and products, Redis carts, orders, Stripe payments, Celery email tasks, and Alembic migrations.

## Stack

- Python 3.11+
- FastAPI, Uvicorn, Pydantic v2
- PostgreSQL, SQLAlchemy async, asyncpg
- Redis and Celery
- Stripe Checkout and webhooks
- Alembic
- Docker Compose

## Project layout

```text
app/
|-- api/v1/endpoints/   API route modules
|-- core/               settings, database, Redis, security, Celery
|-- models/             SQLAlchemy models
|-- schemas/            Pydantic request and response schemas
|-- services/           business logic
|-- tasks/              Celery tasks
alembic/                database migrations
tests/                  async API tests with SQLite and fake Redis
docker-compose.yml      PostgreSQL, Redis, API, and pgAdmin services
```

## Configuration

Create `.env` in the project root. Docker Compose reads this file for the `web` service. The repository includes `.env.example` as a starting point.

Required values:

```env
SECRET_KEY=replace-with-a-long-random-secret
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-email-password-or-app-password
```

For local execution, use `POSTGRES_HOST=localhost` and `REDIS_URL=redis://localhost:6379/0`. Inside Docker Compose, the defaults use the service names `db` and `redis`.

Never commit real secrets, passwords, tokens, or production credentials.

## Run with Docker Compose

```powershell
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- pgAdmin: `http://localhost:5050`

Apply migrations from the API container or a local environment:

```powershell
docker compose exec web alembic upgrade head
```

## Run locally

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start PostgreSQL and Redis, configure `.env`, then run:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

## API routes

Routes are currently mounted at the root. There is no `/api` or `/v1` prefix in the application.

| Area | Routes |
| --- | --- |
| Auth | `/auth/register`, `/auth/login/`, `/auth/refresh`, `/auth/me` |
| Users | `/users/`, `/users/me`, role, password, ban, profile, and delete operations |
| Stores | `/stores/` and store detail, update, delete, logo, and banner operations |
| Categories | `/categories/` and category detail, create, update, and delete operations |
| Products | `/products/`, product detail, create, update, delete, and image upload |
| Cart | `/cart/`, `/cart/items`, and cart item removal/clear operations |
| Orders | `/orders/checkout`, order listing, detail, and cancellation |
| Payments | Stripe checkout, webhook, payment listing, detail, and refund operations |

Use Swagger UI at `/docs` for the complete request and response schemas. Admin-only and seller-only operations require a Bearer access token with the appropriate role.

## Tests

Tests use an isolated in-memory SQLite database and a fake Redis implementation, so the API test suite does not require running PostgreSQL, Redis, Stripe, or Celery.

```powershell
.\env\Scripts\python.exe -m pytest -q
```

The suite covers authentication, authorization, users, stores, categories, products, uploads, carts, orders, payments, refunds, and webhook idempotency.

## Celery worker

Start Redis first, then run the worker in a separate terminal:

```powershell
celery -A app.core.celery_app worker --loglevel=info
```

## Stripe webhook testing

With the API running, forward Stripe events to the webhook endpoint:

```powershell
stripe listen --forward-to localhost:8000/payments/webhook
```

Copy the displayed webhook signing secret into `STRIPE_WEBHOOK_SECRET`. The endpoint requires the `Stripe-Signature` header.

## Migrations

After changing SQLAlchemy models:

```powershell
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Security notes

Use strong, unique values for `SECRET_KEY`, database passwords, Stripe keys, and SMTP credentials. Do not use test credentials in production. Validate uploaded files and configure HTTPS before exposing the service publicly.

## License

No license has been specified yet. Add a license before distributing this project publicly.
