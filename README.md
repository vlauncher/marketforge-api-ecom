# MarketForge API

A multi-vendor commerce platform built with FastAPI, featuring asynchronous operations throughout, SQLAlchemy 2.0, PostgreSQL, and Redis.

## Features

- **Multi-Vendor Support**: Vendors can onboard, manage stores, products, and fulfill orders
- **Storefronts**: Customizable storefronts with themes and pages
- **Product Catalog**: Full catalog management with categories, brands, variants, and addons
- **Pricing Engine**: Multi-currency support with real-time exchange rates
- **Inventory Management**: Transactional inventory with reservation and commit flow
- **Shopping Cart**: Session-based and user-associated cart management
- **Checkout**: Idempotent checkout with address management
- **Orders & Fulfillment**: Complete order lifecycle with shipment tracking
- **Payments**: Payment processing with refund support
- **Promotions**: Coupons, promotions, and gift cards
- **Reviews & Ratings**: Product reviews with approval workflow
- **Customers**: Wishlists and loyalty program with tiered rewards
- **Analytics**: Sales analytics and vendor payout processing

## Tech Stack

- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async)
- **Cache**: Redis
- **Authentication**: JWT with access/refresh tokens
- **Validation**: Pydantic v2

## Project Structure

```
marketforge-api-ecom/
├── app/
│   ├── core/           # Core infrastructure
│   │   ├── config.py       # Configuration management
│   │   ├── database.py    # Database connection and session
│   │   ├── redis.py       # Redis client
│   │   ├── security.py    # JWT and password utilities
│   │   ├── exceptions.py   # Custom exceptions
│   │   └── logging.py     # Logging setup
│   ├── modules/        # Domain modules
│   │   ├── identity/      # User authentication
│   │   ├── vendors/        # Vendor management
│   │   ├── storefronts/    # Store management
│   │   ├── catalog/        # Product catalog
│   │   ├── pricing/        # Pricing and currencies
│   │   ├── inventory/      # Inventory management
│   │   ├── cart/           # Shopping cart
│   │   ├── checkout/       # Checkout processing
│   │   ├── orders/         # Order management
│   │   ├── payments/       # Payment processing
│   │   ├── promotions/     # Coupons and promotions
│   │   ├── reviews/        # Product reviews
│   │   ├── customers/      # Wishlist and loyalty
│   │   ├── fulfillment/    # Shipment tracking
│   │   └── analytics/      # Analytics and payouts
│   └── main.py         # Application factory
├── tests/              # Test suite
│   ├── conftest.py        # Test fixtures
│   ├── unit/              # Unit tests
│   └── integration/        # Integration tests
└── alembic/           # Database migrations
```

## Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 16+ (or Docker)
- Redis 7+ (or Docker)

### 1. Clone and Setup Environment

```bash
# Clone the repository
cd marketforge-api-ecom

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
```

### 2. Start Infrastructure with Docker Compose

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 3. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 4. Initialize Database

```bash
# Run database migrations
alembic upgrade head

# Or create tables directly (development only)
python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 5. Run the Application

```bash
# Development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. Access API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Configuration

Environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | postgresql+asyncpg://... |
| `REDIS_URL` | Redis connection string | redis://localhost:6379/0 |
| `SECRET_KEY` | JWT signing key | - |
| `ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiry | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | 7 |
| `CORS_ORIGINS` | Allowed CORS origins | http://localhost:3000 |
| `LOG_LEVEL` | Logging level | INFO |

## Testing

### Run All Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio aiosqlite httpx

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_pricing.py -v
```

## API Modules

| Module | Prefix | Description |
|--------|--------|-------------|
| Authentication | `/auth` | User registration, login, token refresh |
| Vendors | `/vendors` | Vendor management |
| Storefronts | `/stores` | Store browsing |
| Catalog | `/products`, `/categories`, `/brands` | Product catalog |
| Pricing | `/currencies`, `/prices` | Multi-currency pricing |
| Inventory | `/vendor/inventory` | Inventory management |
| Cart | `/cart` | Shopping cart |
| Checkout | `/checkout` | Checkout processing |
| Orders | `/orders` | Order management |
| Payments | `/payments` | Payment processing |
| Promotions | `/promotions`, `/coupons` | Promotional discounts |
| Reviews | `/products/{id}/reviews` | Product reviews |
| Customers | `/customers` | Wishlists, loyalty |
| Fulfillment | `/orders/{id}/shipments` | Shipment tracking |
| Analytics | `/vendors/{id}/analytics`, `/admin/analytics` | Analytics |

## Key Design Patterns

### Idempotent Checkout

The checkout endpoint accepts an `idempotency_key` parameter. If a checkout request with the same key is submitted multiple times, the original order is returned instead of creating duplicates.

### Transactional Inventory

Stock reservation uses `SELECT FOR UPDATE` to prevent overselling under concurrent load. Reserved stock can be committed (sold) or released (cancelled).

### Multi-Currency Pricing

Products can have prices in multiple currencies. The pricing engine resolves prices with full breakdown (base, variant delta, addons, taxes, shipping).

### Async Throughout

All database operations, HTTP calls, and background tasks use async/await for optimal performance.

## License

MIT License