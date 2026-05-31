# Multi-Vendor Commerce Platform Implementation Plan

## Overview

Build a FastAPI-based multi-vendor commerce backend from scratch following a modular architecture with 14 domain modules.

## Project Structure

```
marketforge-api-ecom/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application factory
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                # Pydantic settings (env vars)
│   │   ├── database.py              # SQLAlchemy async engine + session
│   │   ├── redis.py                 # Redis connection pool
│   │   ├── security.py              # JWT utilities, password hashing
│   │   ├── dependencies.py          # Common dependencies (get_db, get_current_user)
│   │   ├── exceptions.py            # Domain exceptions + handlers
│   │   └── logging.py               # Structured logging setup
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   │
│   │   ├── identity/                # User authentication & authorization
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # User, Role, Permission models
│   │   │   ├── schemas.py           # Login, Register, Token schemas
│   │   │   ├── router.py            # Auth endpoints
│   │   │   ├── service.py           # Auth business logic
│   │   │   └── dependencies.py      # get_current_user, require_role
│   │   │
│   │   ├── vendors/                 # Vendor management
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Vendor, VendorProfile
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   ├── storefronts/             # Store management
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Store, StoreTheme, StorePage, StoreDomain
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   ├── catalog/                 # Product catalog
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Product, Variant, Attribute, Addon, Image, Category, Brand
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   ├── service.py
│   │   │   └── search.py            # Search & filter logic
│   │   │
│   │   ├── pricing/                 # Multi-currency pricing engine
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Price, Currency, ExchangeRate
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   ├── service.py           # Price resolution, breakdown calculation
│   │   │   └── exchange_rates.py    # External rate provider integration
│   │   │
│   │   ├── inventory/               # Stock management
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # InventoryLocation, InventoryItem, InventoryMovement
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py           # Reservation logic
│   │   │
│   │   ├── cart/                    # Shopping cart
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Cart, CartItem
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   ├── checkout/                # Checkout orchestration
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   ├── service.py           # Idempotent checkout flow
│   │   │   └── idempotency.py       # Idempotency key handling
│   │   │
│   │   ├── payments/                # Payment processing
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Payment, Refund
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   ├── promotions/              # Discounts & promotions
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Coupon, Promotion, GiftCard
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   ├── orders/                  # Order management
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Order, OrderItem, Shipment
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   ├── fulfillment/             # Shipping & delivery
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Shipment tracking
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   ├── reviews/                 # Customer reviews
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Review, Rating
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   ├── analytics/               # Vendor & admin analytics
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # VendorPayout, analytics aggregations
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   ├── customers/               # Customer-specific features
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # Wishlist, LoyaltyAccount
│   │   │   ├── schemas.py
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   └── notifications/           # Email/webhook notifications
│   │       ├── __init__.py
│   │       ├── models.py
│   │       ├── schemas.py
│   │       ├── router.py
│   │       └── service.py
│   │
│   └── workers/                     # Background task workers
│       ├── __init__.py
│       ├── exchange_rate_worker.py  # Periodic exchange rate updates
│       └── order_worker.py          # Order processing tasks
│
├── tests/
│   ├── conftest.py                  # Shared fixtures
│   ├── unit/
│   │   ├── test_pricing_engine.py
│   │   ├── test_currency_conversion.py
│   │   ├── test_inventory_reservation.py
│   │   ├── test_coupon_logic.py
│   │   └── test_variant_resolution.py
│   └── integration/
│       ├── test_storefront.py
│       ├── test_catalog.py
│       ├── test_cart_checkout.py
│       ├── test_orders.py
│       └── test_auth.py
│
├── alembic/
│   ├── env.py
│   └── versions/
│
├── alembic.ini
├── docker-compose.yml               # PostgreSQL + Redis
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

## Database Schema Design

### Core Tables

```sql
-- Identity & Auth
users (id, email, password_hash, role, is_active, created_at, updated_at)

-- Vendors
vendors (id, user_id FK, name, slug UNIQUE, status, commission_rate, created_at)
vendor_profiles (id, vendor_id FK, bio, logo_url, contact_email, phone, address)

-- Stores
stores (id, vendor_id FK, name, slug UNIQUE, description, is_active, created_at)
store_themes (id, store_id FK, colors JSON, fonts JSON, layout JSON)
store_pages (id, store_id FK, slug, title, content, page_type, is_published)
store_domains (id, store_id FK, domain UNIQUE, is_primary, is_verified)

-- Catalog
categories (id, parent_id FK NULL, name, slug, description, sort_order)
brands (id, name, slug, logo_url)
products (id, store_id FK, category_id FK, brand_id FK, name, slug, description, product_type, status, created_at)
product_variants (id, product_id FK, sku UNIQUE, attributes JSON, is_active)
product_attributes (id, product_id FK, name, values JSON)
product_attribute_values (id, attribute_id FK, value, sort_order)
product_images (id, product_id FK, url, alt_text, sort_order, is_primary)
addon_groups (id, product_id FK, name, is_required, min_select, max_select)
product_addons (id, addon_group_id FK, name, description, price_delta)

-- Pricing
currencies (id, code UNIQUE, name, symbol, decimal_places, is_active)
exchange_rates (id, from_currency_id FK, to_currency_id FK, rate, effective_at, created_at)
prices (id, product_id FK, variant_id FK NULL, addon_id FK NULL, currency_id FK, amount, is_override, effective_from, effective_until)

-- Inventory
inventory_locations (id, store_id FK, name, address, is_active)
inventory_items (id, location_id FK, product_id FK, variant_id FK NULL, quantity, reserved_quantity)
inventory_movements (id, inventory_item_id FK, quantity_change, movement_type, reference_id, created_at)

-- Cart
carts (id, user_id FK NULL, session_id, store_id FK, created_at, updated_at)
cart_items (id, cart_id FK, product_id FK, variant_id FK NULL, quantity, selected_addons JSON)

-- Orders
orders (id, user_id FK NULL, store_id FK, order_number UNIQUE, status, subtotal, tax_amount, shipping_amount, discount_amount, total, currency_id FK, shipping_address JSON, billing_address JSON, idempotency_key UNIQUE, created_at)
order_items (id, order_id FK, product_id FK, variant_id FK NULL, name, quantity, unit_price, addons JSON, total_price)

-- Payments
payments (id, order_id FK, amount, currency_id FK, status, payment_method, transaction_id, idempotency_key UNIQUE, created_at)
refunds (id, payment_id FK, amount, reason, status, created_at)

-- Promotions
coupons (id, store_id FK, code UNIQUE, discount_type, discount_value, min_order_amount, max_uses, uses_count, valid_from, valid_until, is_active)
promotions (id, store_id FK, name, discount_type, discount_value, applies_to, conditions JSON, is_active, valid_from, valid_until)
gift_cards (id, store_id FK, code UNIQUE, initial_balance, current_balance, currency_id FK, is_active)

-- Fulfillment
shipments (id, order_id FK, carrier, tracking_number, status, shipped_at, delivered_at)

-- Reviews
reviews (id, product_id FK, user_id FK, rating, title, comment, is_approved, created_at)
ratings (id, product_id FK, average_rating, total_reviews)

-- Customer Features
wishlists (id, user_id FK, product_id FK, created_at)
loyalty_accounts (id, user_id FK, points, tier, created_at)

-- Vendor Operations
vendor_payouts (id, vendor_id FK, amount, currency_id FK, status, period_start, period_end, processed_at)
```

### Key Indexes

```sql
CREATE INDEX idx_stores_slug ON stores(slug);
CREATE INDEX idx_stores_vendor_active ON stores(vendor_id, is_active);
CREATE INDEX idx_products_store_status ON products(store_id, status);
CREATE INDEX idx_products_slug ON products(slug);
CREATE INDEX idx_prices_product_currency ON prices(product_id, currency_id);
CREATE INDEX idx_prices_variant_currency ON prices(variant_id, currency_id);
CREATE INDEX idx_inventory_item_variant ON inventory_items(location_id, product_id, variant_id);
CREATE INDEX idx_orders_store_created ON orders(store_id, created_at);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_exchange_rates_effective ON exchange_rates(from_currency_id, to_currency_id, effective_at);
CREATE INDEX idx_coupons_code ON coupons(code);
```

## Implementation Steps

### Phase 1: Project Foundation & Infrastructure

1. **Initialize project structure**
   - Create `pyproject.toml` with dependencies (fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, pydantic-settings, python-jose, passlib, redis, httpx, pytest, pytest-asyncio, alembic)
   - Create `.env.example` with required environment variables
   - Create `docker-compose.yml` for PostgreSQL and Redis

2. **Core infrastructure** (`app/core/`)
   - `config.py`: Pydantic Settings class for environment configuration
   - `database.py`: Async SQLAlchemy engine, session factory, Base model
   - `redis.py`: Redis connection pool for caching and sessions
   - `security.py`: JWT token creation/verification, password hashing with bcrypt
   - `exceptions.py`: Custom exceptions (NotFound, Unauthorized, ValidationError, ConflictError)
   - `dependencies.py`: Common dependencies (get_db, get_current_user, get_optional_user)
   - `logging.py`: Structured JSON logging with correlation IDs

3. **Application factory** (`app/main.py`)
   - FastAPI app with lifespan for startup/shutdown
   - CORS middleware
   - Exception handlers
   - Router registration
   - Health check endpoint

4. **Alembic setup**
   - Initialize alembic with async support
   - Configure `env.py` to use app models

### Phase 2: Identity Module (Authentication & Authorization)

**Files:** `app/modules/identity/`

1. **Models** (`models.py`)
   - `User` model with id, email, password_hash, role (customer/vendor/admin), is_active, timestamps

2. **Schemas** (`schemas.py`)
   - `UserCreate`, `UserLogin`, `UserResponse`, `Token`, `TokenRefresh`

3. **Service** (`service.py`)
   - `register_user()`: Create user with hashed password
   - `authenticate()`: Verify credentials, return JWT
   - `refresh_token()`: Issue new access token
   - `get_user_by_id()`: Fetch user

4. **Router** (`router.py`)
   - `POST /auth/register`
   - `POST /auth/login`
   - `POST /auth/refresh`
   - `GET /auth/me`

5. **Dependencies** (`dependencies.py`)
   - `get_current_user`: Extract and validate JWT from Authorization header
   - `get_optional_user`: Return user if authenticated, None otherwise
   - `require_role(role)`: Factory for role-based access control

### Phase 3: Vendor & Store Modules

**Files:** `app/modules/vendors/`, `app/modules/storefronts/`

1. **Vendor Models**
   - `Vendor`: id, user_id (FK), name, slug, status (pending/verified/suspended), commission_rate
   - `VendorProfile`: vendor_id (FK), bio, logo_url, contact info

2. **Store Models**
   - `Store`: id, vendor_id (FK), name, slug (unique), description, is_active
   - `StoreTheme`: store_id (FK), colors (JSON), fonts (JSON), layout (JSON)
   - `StorePage`: store_id (FK), slug, title, content, page_type, is_published
   - `StoreDomain`: store_id (FK), domain (unique), is_primary, is_verified

3. **Vendor Service & Router**
   - `POST /vendors/onboard`: Create vendor + default store
   - `GET /vendors/{id}`: Get vendor details
   - `PATCH /vendors/{id}`: Update vendor profile
   - `PATCH /vendors/{id}/status`: Admin-only status change

4. **Storefront Service & Router**
   - `GET /stores`: List active stores
   - `GET /stores/{slug}`: Get store details with theme
   - `GET /stores/{slug}/pages/{page_slug}`: Get store page
   - `POST /vendor/stores`: Create store (vendor only)
   - `PATCH /vendor/stores/{id}`: Update store
   - `POST /vendor/stores/{id}/theme`: Update theme
   - `POST /vendor/stores/{id}/pages`: Create page

### Phase 4: Catalog Module

**Files:** `app/modules/catalog/`

1. **Models**
   - `Category`: id, parent_id (self-ref FK), name, slug, description, sort_order
   - `Brand`: id, name, slug, logo_url
   - `Product`: id, store_id (FK), category_id (FK), brand_id (FK), name, slug, description, product_type (simple/variable/bundle/subscription/digital), status
   - `ProductVariant`: id, product_id (FK), sku (unique), attributes (JSON), is_active
   - `ProductAttribute`: id, product_id (FK), name, values (JSON)
   - `ProductImage`: id, product_id (FK), url, alt_text, sort_order, is_primary
   - `AddonGroup`: id, product_id (FK), name, is_required, min_select, max_select
   - `ProductAddon`: id, addon_group_id (FK), name, description, price_delta

2. **Schemas**
   - Full CRUD schemas for products, variants, addons, categories, brands
   - Nested response schemas for product detail with variants and addons

3. **Service**
   - Product CRUD with store ownership validation
   - Variant management with SKU uniqueness
   - Addon group and addon management
   - Category tree operations
   - Product image management

4. **Router**
   - `GET /stores/{slug}/products`: List store products
   - `GET /stores/{slug}/products/{product_slug}`: Get product detail
   - `GET /stores/{slug}/collections`: Get featured collections
   - `POST /vendor/products`: Create product
   - `PATCH /vendor/products/{id}`: Update product
   - `POST /vendor/products/{id}/variants`: Add variant
   - `POST /vendor/products/{id}/addons`: Add addon
   - `POST /vendor/products/{id}/images`: Upload image
   - `GET /products/search`: Search products
   - `GET /products/filter`: Filter products

5. **Search** (`search.py`)
   - Full-text search on product name and description
   - Filter by category, brand, price range, attributes
   - Pagination and sorting

### Phase 5: Pricing Module (Multi-Currency Engine)

**Files:** `app/modules/pricing/`

1. **Models**
   - `Currency`: id, code (unique), name, symbol, decimal_places, is_active
   - `ExchangeRate`: id, from_currency_id (FK), to_currency_id (FK), rate, effective_at, created_at
   - `Price`: id, product_id (FK), variant_id (FK nullable), addon_id (FK nullable), currency_id (FK), amount, is_override, effective_from, effective_until

2. **Service** (`service.py`) - **Core Pricing Engine**
   ```python
   async def resolve_price(product_id, variant_id, addon_ids, currency) -> PriceBreakdown:
       # 1. Get base price for product in requested currency
       # 2. Add variant price delta if variant selected
       # 3. Add addon price deltas for selected addons
       # 4. Apply any active promotions
       # 5. Convert currency if no direct price exists (use exchange rate)
       # 6. Calculate tax estimate
       # 7. Calculate shipping estimate
       # 8. Return full breakdown
   ```

3. **Exchange Rate Service** (`exchange_rates.py`)
   - Integration with external rate provider (e.g., exchangerate-api.com)
   - Rate caching in Redis
   - Rate versioning with effective_at timestamps

4. **Router**
   - `GET /pricing/{product_id}`: Get price breakdown
   - `GET /admin/currencies`: List currencies
   - `POST /admin/currencies`: Add currency
   - `POST /admin/exchange-rates/update`: Trigger rate update
   - `GET /admin/exchange-rates`: View rate history

### Phase 6: Inventory Module

**Files:** `app/modules/inventory/`

1. **Models**
   - `InventoryLocation`: id, store_id (FK), name, address, is_active
   - `InventoryItem`: id, location_id (FK), product_id (FK), variant_id (FK nullable), quantity, reserved_quantity
   - `InventoryMovement`: id, inventory_item_id (FK), quantity_change, movement_type (received/sold/reserved/released/adjusted), reference_id, created_at

2. **Service** - **Transactional Reservation**
   ```python
   async def reserve_stock(items: list[ReservationItem], db_session) -> ReservationResult:
       # Use SELECT FOR UPDATE to prevent race conditions
       # Check available = quantity - reserved_quantity
       # Increment reserved_quantity
       # Create inventory_movements
       # Return success/failure with details
   ```

3. **Router**
   - `GET /vendor/inventory`: List inventory by location
   - `POST /vendor/inventory/locations`: Add location
   - `POST /vendor/inventory/adjust`: Manual stock adjustment
   - `GET /vendor/inventory/low-stock`: Low stock alerts

### Phase 7: Cart Module

**Files:** `app/modules/cart/`

1. **Models**
   - `Cart`: id, user_id (FK nullable), session_id, store_id (FK), created_at, updated_at
   - `CartItem`: id, cart_id (FK), product_id (FK), variant_id (FK nullable), quantity, selected_addons (JSON)

2. **Service**
   - Cart persistence (user-based or session-based for guests)
   - Add/update/remove items
   - Validate stock availability
   - Calculate cart totals using pricing engine

3. **Router**
   - `GET /cart`: Get current cart
   - `POST /cart/items`: Add item to cart
   - `PATCH /cart/items/{id}`: Update quantity/addons
   - `DELETE /cart/items/{id}`: Remove item
   - `POST /cart/merge`: Merge guest cart into user cart on login

### Phase 8: Checkout & Orders Module

**Files:** `app/modules/checkout/`, `app/modules/orders/`

1. **Checkout Schemas**
   - `CheckoutRequest`: cart_id, shipping_address, billing_address, payment_method, coupon_code (optional), idempotency_key
   - `CheckoutResponse`: order_id, order_number, payment_intent_id, total

2. **Checkout Service** - **Idempotent Transaction**
   ```python
   async def process_checkout(request: CheckoutRequest, idempotency_key: str) -> Order:
       # Check idempotency - return existing order if key exists
       # Validate cart and stock
       # Apply coupon if provided
       # Calculate final totals with pricing engine
       # Reserve inventory (transactional)
       # Create order (append-only after this point)
       # Create payment intent
       # Clear cart
       # Trigger async notifications
   ```

3. **Order Models**
   - `Order`: id, user_id, store_id, order_number, status, subtotal, tax, shipping, discount, total, currency_id, addresses (JSON), idempotency_key
   - `OrderItem`: id, order_id, product_id, variant_id, name, quantity, unit_price, addons (JSON), total_price

4. **Order Router**
   - `POST /checkout`: Process checkout
   - `POST /checkout/apply-coupon`: Validate and preview coupon
   - `POST /checkout/calculate-shipping`: Get shipping options
   - `POST /checkout/calculate-tax`: Get tax estimate
   - `GET /orders`: List user orders
   - `GET /orders/{id}`: Get order detail
   - `POST /orders/{id}/cancel`: Cancel order (if eligible)

### Phase 9: Payments Module

**Files:** `app/modules/payments/`

1. **Models**
   - `Payment`: id, order_id, amount, currency_id, status (pending/completed/failed/refunded), payment_method, transaction_id, idempotency_key
   - `Refund`: id, payment_id, amount, reason, status, created_at

2. **Service**
   - Payment intent creation
   - Payment confirmation (webhook handler for payment provider)
   - Refund processing with inventory release

3. **Router**
   - `POST /payments/webhook`: Payment provider webhook
   - `GET /vendor/payments`: List vendor payments
   - `POST /orders/{id}/refund`: Initiate refund (admin/vendor)

### Phase 10: Promotions Module

**Files:** `app/modules/promotions/`

1. **Models**
   - `Coupon`: id, store_id, code, discount_type (percentage/fixed), discount_value, min_order_amount, max_uses, uses_count, valid_from, valid_until, is_active
   - `Promotion`: id, store_id, name, discount_type, discount_value, applies_to (JSON), conditions (JSON), is_active, dates
   - `GiftCard`: id, store_id, code, initial_balance, current_balance, currency_id, is_active

2. **Service**
   - Coupon validation and application
   - Promotion eligibility checking
   - Gift card balance management
   - Stacking rules (can coupons and promotions combine?)

3. **Router**
   - `POST /vendor/coupons`: Create coupon
   - `GET /vendor/coupons`: List coupons
   - `PATCH /vendor/coupons/{id}`: Update coupon
   - `POST /vendor/promotions`: Create promotion
   - `POST /vendor/gift-cards`: Create gift card

### Phase 11: Reviews & Customer Features

**Files:** `app/modules/reviews/`, `app/modules/customers/`

1. **Review Models**
   - `Review`: id, product_id, user_id, rating (1-5), title, comment, is_approved, created_at
   - `Rating`: id, product_id, average_rating, total_reviews (denormalized for performance)

2. **Customer Models**
   - `Wishlist`: id, user_id, product_id, created_at
   - `LoyaltyAccount`: id, user_id, points, tier, created_at

3. **Routers**
   - `POST /products/{id}/reviews`: Submit review
   - `GET /products/{id}/reviews`: List reviews
   - `POST /admin/reviews/{id}/approve`: Moderate review
   - `POST /wishlist`: Add to wishlist
   - `GET /wishlist`: Get wishlist
   - `DELETE /wishlist/{id}`: Remove from wishlist
   - `GET /loyalty`: Get loyalty balance

### Phase 12: Fulfillment Module

**Files:** `app/modules/fulfillment/`

1. **Models**
   - `Shipment`: id, order_id, carrier, tracking_number, status, shipped_at, delivered_at

2. **Service**
   - Create shipment on order fulfillment
   - Update tracking status
   - Release inventory reservation on shipment

3. **Router**
   - `GET /orders/{id}/shipments`: Get order shipments
   - `POST /vendor/orders/{id}/ship`: Create shipment
   - `PATCH /vendor/shipments/{id}`: Update shipment status

### Phase 13: Analytics & Payouts

**Files:** `app/modules/analytics/`

1. **Models**
   - `VendorPayout`: id, vendor_id, amount, currency_id, status, period_start, period_end, processed_at

2. **Service**
   - Sales aggregation queries
   - Commission calculation
   - Payout generation and processing

3. **Router**
   - `GET /vendors/{id}/analytics`: Vendor dashboard data
   - `GET /vendors/{id}/payouts`: List payouts
   - `GET /admin/analytics`: Platform-wide analytics
   - `POST /admin/payouts/process`: Trigger payout processing

### Phase 14: Testing

1. **Unit Tests**
   - Pricing engine calculations
   - Currency conversion with rounding rules
   - Variant price resolution
   - Addon pricing aggregation
   - Coupon discount logic
   - Inventory reservation logic (including race conditions)

2. **Integration Tests**
   - Auth flow (register, login, token refresh)
   - Storefront browsing
   - Vendor product CRUD
   - Cart operations
   - Full checkout flow with inventory reservation
   - Multi-currency order totals
   - Refund flow
   - Idempotency verification

3. **Test Fixtures** (`tests/conftest.py`)
   - Async test database setup
   - Test client factory
   - User/vendor/store fixtures
   - Product catalog fixtures
   - Mock exchange rate provider

### Phase 15: Documentation & Polish

1. **OpenAPI documentation**
   - Add detailed docstrings to all endpoints
   - Add request/response examples
   - Tag endpoints by module

2. **README.md**
   - Project overview
   - Setup instructions (docker-compose, env vars)
   - Running tests
   - API documentation link

## Key Design Decisions

1. **Modular Architecture**: Each domain is self-contained with its own models, schemas, service, and router. Modules communicate through well-defined service interfaces.

2. **Async Throughout**: SQLAlchemy 2.0 async sessions, async HTTP client for external APIs, async background workers.

3. **Idempotent Checkout**: Checkout endpoint accepts idempotency_key to prevent duplicate orders. Key is stored with order and checked before processing.

4. **Transactional Inventory**: Stock reservation uses `SELECT FOR UPDATE` to prevent overselling under concurrent load.

5. **Price Breakdown**: Every price response includes full breakdown (base, variant, addons, promotions, tax, shipping) for transparency.

6. **Multi-Currency Storage**: Prices are stored per currency, not just calculated on-demand. Exchange rates are versioned with effective_at timestamps.

7. **Append-Only Orders**: Once an order is placed, it cannot be modified. Changes create new records (refunds, cancellations update status but don't delete).

## Verification Plan

1. **Start services**: `docker-compose up -d` (PostgreSQL + Redis)
2. **Run migrations**: `alembic upgrade head`
3. **Start server**: `uvicorn app.main:app --reload`
4. **Run tests**: `pytest tests/ -v`
5. **Test endpoints**: Use Swagger UI at `/docs`
6. **Verify idempotency**: Send same checkout request twice with same idempotency_key
7. **Verify currency conversion**: Create product with USD price, fetch in EUR
8. **Verify inventory**: Create order, check stock reserved, cancel order, check stock released
