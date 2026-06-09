# MarketForge Frontend Integration Plan

A world-class React + TypeScript + Vite + Tailwind frontend for the MarketForge multi-vendor commerce platform.

---

## Table of Contents

1. Executive Summary
2. Verified API Route Map
3. Critical Implementation Notes
4. Tech Stack & Architecture
5. Project Structure
6. UI/UX Design System
7. State Management Strategy
8. Authentication & Authorization
9. Customer-Facing Flows
10. Vendor Dashboard
11. Admin Console
12. TypeScript Types & Enums
13. Error Handling Contract
14. Implementation Roadmap
15. Local Development Setup

---

## 1. Executive Summary

This document is the **definitive guide** for building a production-grade, multi-tenant e-commerce frontend that integrates with the MarketForge FastAPI backend.

**Backend scope**:
- 15 domain modules
- 3 user roles (customer, vendor, admin)
- 4 payment gateways (Stripe, Paystack, Flutterwave, Monnify)
- JWT auth with access/refresh tokens
- Idempotent checkout, transactional inventory, multi-currency pricing
- Webhook support for all payment providers

**Frontend goals**:
- Single-page application with role-aware routing
- Real-time updates and optimistic UI
- World-class UX (motion, accessibility, mobile-first)
- Type-safe end-to-end (TypeScript strict, Zod validation)
- Generated types from OpenAPI schema for guaranteed contract safety

---

## 2. Verified API Route Map

All routes below were extracted directly from the router files (`@router.*`, `@vendor_router.*`, `@admin_router.*` decorators) and verified against the `APIRouter(prefix=...)` declarations. **This is the source of truth for frontend integration.**

### 2.1 Authentication & Identity — prefix=/auth

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /auth/register | Public | Register new user (returns UserResponse) |
| POST | /auth/login | Public | Login returns access + refresh tokens |
| POST | /auth/refresh | Public | Refresh access token |
| GET | /auth/me | Bearer | Get current user profile |

### 2.2 Vendors — prefix=/vendors

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /vendors/onboard | Public | Self-service vendor onboarding (user + vendor + store) |
| GET | /vendors/{vendor_id} | Public | Get vendor public profile |
| PATCH | /vendors/{vendor_id} | Bearer (owner) | Update vendor |
| PATCH | /vendors/{vendor_id}/status | Bearer (admin) | Approve/suspend vendor |
| GET | /vendors/me/profile | Bearer (vendor) | Get own vendor profile |

### 2.3 Storefronts

**Public router** (no prefix):

| Method | Path | Purpose |
|--------|------|---------|
| GET | /stores | List active stores (limit/offset pagination) |
| GET | /stores/{slug} | Get store details + theme + pages + domains |
| GET | /stores/{store_slug}/pages/{page_slug} | Get a custom store page |

**Vendor router** — prefix=/vendor/stores:

| Method | Path | Purpose |
|--------|------|---------|
| POST | /vendor/stores | Create a new store |
| PATCH | /vendor/stores/{store_id} | Update store |
| POST | /vendor/stores/{store_id}/theme | Create or update theme (colors/fonts/layout) |
| POST | /vendor/stores/{store_id}/pages | Create a page |
| PATCH | /vendor/stores/{store_id}/pages/{page_id} | Update a page |

### 2.4 Catalog

**Public router** (no prefix):

| Method | Path | Purpose |
|--------|------|---------|
| GET | /stores/{store_slug}/products | List products for a store |
| GET | /stores/{store_slug}/products/{product_slug} | Get product detail with variants/attributes/images/addon_groups |
| GET | /stores/{store_slug}/collections | Get featured collections (grouped by category) |
| GET | /products/search | Advanced search with filters (query, category, brand, store, price range, sort) |
| GET | /categories | List categories (optional parent_id filter) |
| GET | /brands | List brands |

**Vendor router** — prefix=/vendor:

| Method | Path | Purpose |
|--------|------|---------|
| POST | /vendor/products | Create product |
| PATCH | /vendor/products/{product_id} | Update product |
| DELETE | /vendor/products/{product_id} | Delete product |
| POST | /vendor/products/{product_id}/variants | Add variant |
| PATCH | /vendor/products/{product_id}/variants/{variant_id} | Update variant |
| POST | /vendor/products/{product_id}/attributes | Add product attribute |
| POST | /vendor/products/{product_id}/images | Add product image |
| POST | /vendor/products/{product_id}/addon-groups | Create addon group |
| POST | /vendor/addon-groups/{group_id}/addons | Add addon to group |

---

### 2.5 Pricing

**Public router** — prefix=/pricing:

| Method | Path | Purpose |
|--------|------|---------|
| GET | /pricing/{product_id} | Resolve price with full breakdown (variant, addons, tax, discount, currency conversion) |
| GET | /pricing/currencies | List active currencies |

**Admin router** — prefix=/admin:

| Method | Path | Purpose |
|--------|------|---------|
| GET | /admin/exchange-rates | List exchange rates |
| POST | /admin/currencies | Create currency |
| PATCH | /admin/currencies/{currency_id} | Update currency |
| POST | /admin/exchange-rates/update | Trigger external rate provider fetch |

### 2.6 Inventory (vendor only) — prefix=/vendor/inventory

| Method | Path | Purpose |
|--------|------|---------|
| GET | /vendor/inventory/locations | List inventory locations |
| POST | /vendor/inventory/locations | Create location |
| PATCH | /vendor/inventory/locations/{location_id} | Update location |
| GET | /vendor/inventory/ | List inventory items (filter by location_id, product_id) |
| POST | /vendor/inventory/adjust | Adjust stock (query params: location_id, product_id, variant_id) |
| POST | /vendor/inventory/reserve | Reserve stock for an order |
| POST | /vendor/inventory/release | Release reservation (by order_id) |
| GET | /vendor/inventory/low-stock | Get low-stock alerts |
| GET | /vendor/inventory/movements | Get movement history |

### 2.7 Cart — prefix=/cart (hybrid auth: Bearer OR ?session_id=)

| Method | Path | Purpose |
|--------|------|---------|
| GET | /cart | Get current cart (auto-created) |
| POST | /cart/items | Add item (product_id, variant_id, quantity, selected_addons) |
| PATCH | /cart/items/{item_id} | Update item (quantity, addons) |
| DELETE | /cart/items/{item_id} | Remove item |
| POST | /cart/merge | Merge guest cart into user cart on login |
| DELETE | /cart | Clear all items |

### 2.8 Checkout — prefix=/checkout

| Method | Path | Purpose |
|--------|------|---------|
| POST | /checkout | Process checkout (**idempotency_key required**) |
| POST | /checkout/apply-coupon | Validate coupon + get discount amount |
| GET | /checkout/calculate-shipping | Get shipping rates (query: cart_id, country) |
| GET | /checkout/calculate-tax | Get tax estimate (query: cart_id, country) |

### 2.9 Orders

**Customer router** — prefix=/orders:

| Method | Path | Purpose |
|--------|------|---------|
| GET | /orders | List my orders |
| GET | /orders/{order_id} | Get order detail |
| GET | /orders/{order_number}/number | Lookup by order number (literal "number" in path) |
| POST | /orders/{order_id}/cancel | Cancel an order |

**Vendor router** — prefix=/vendor/orders:

| Method | Path | Purpose |
|--------|------|---------|
| GET | /vendor/orders | List store orders (filter by status) |
| POST | /vendor/orders/{order_id}/ship | Create shipment for an order |
| PATCH | /vendor/orders/shipments/{shipment_id} | Update shipment (status, tracking, timestamps) |
| GET | /vendor/orders/{order_id}/shipments | List shipments for an order |

### 2.10 Payments

**Customer router** — prefix=/payments:

| Method | Path | Purpose |
|--------|------|---------|
| POST | /payments/webhook | Generic webhook receiver |
| GET | /payments/{payment_id} | Get payment detail with refunds |
| POST | /payments/{payment_id}/refund | Create refund (admin or vendor only) |
| POST | /payments/{order_id}/pay | Create + process payment for an order |

**Vendor router** — prefix=/vendor/payments:

| Method | Path | Purpose |
|--------|------|---------|
| GET | /vendor/payments | List vendor's payments |

**Webhook router** — prefix=/webhooks:

| Method | Path | Purpose |
|--------|------|---------|
| POST | /webhooks/stripe | Stripe webhook |
| POST | /webhooks/paystack | Paystack webhook |
| POST | /webhooks/flutterwave | Flutterwave webhook |
| POST | /webhooks/monnify | Monnify webhook |

---

### 2.11 Promotions

**Public router** (no prefix):

| Method | Path | Purpose |
|--------|------|---------|
| POST | /validate-coupon | Validate coupon code for a subtotal |
| POST | /validate-gift-card | Validate gift card code |

**Vendor router** — prefix=/vendor:

| Method | Path | Purpose |
|--------|------|---------|
| POST | /vendor/coupons | Create coupon |
| GET | /vendor/coupons | List coupons |
| PATCH | /vendor/coupons/{coupon_id} | Update coupon |
| POST | /vendor/promotions | Create promotion |
| GET | /vendor/promotions | List promotions |
| PATCH | /vendor/promotions/{promotion_id} | Update promotion |
| POST | /vendor/gift-cards | Create gift card |
| GET | /vendor/gift-cards | List gift cards |

### 2.12 Reviews

**Public router** — prefix=/products:

| Method | Path | Purpose |
|--------|------|---------|
| POST | /products/{product_id}/reviews | Create a review |
| GET | /products/{product_id}/reviews | List approved reviews |
| GET | /products/{product_id}/rating | Get aggregate rating |
| PATCH | /products/reviews/{review_id} | Update own review |
| DELETE | /products/reviews/{review_id} | Delete own review |

**Admin router** — prefix=/admin/reviews:

| Method | Path | Purpose |
|--------|------|---------|
| POST | /admin/reviews/{review_id}/approve | Approve a review |

### 2.13 Customers — prefix=/customers

| Method | Path | Purpose |
|--------|------|---------|
| POST | /customers/wishlist/{product_id} | Add to wishlist |
| DELETE | /customers/wishlist/{product_id} | Remove from wishlist |
| GET | /customers/wishlist | Get my wishlist |
| GET | /customers/loyalty | Get my loyalty account |
| POST | /customers/loyalty/redeem | Redeem points |
| GET | /customers/loyalty/tiers | List tier definitions |

### 2.14 Fulfillment

**Public router** — prefix=/orders (shares namespace with Orders module):

| Method | Path | Purpose |
|--------|------|---------|
| GET | /orders/{order_id}/shipments | List shipments for an order |
| GET | /orders/{order_id}/shipments/{shipment_id} | Get shipment detail with tracking events |
| POST | /orders/{order_id}/ship | Create a shipment |

**Vendor router** — prefix=/vendor:

| Method | Path | Purpose |
|--------|------|---------|
| POST | /vendor/orders/{order_id}/ship | Create a shipment (vendor) |
| PATCH | /vendor/shipments/{shipment_id} | Update shipment |
| PATCH | /vendor/shipments/{shipment_id}/status | Update status (with location/description) |
| POST | /vendor/shipments/{shipment_id}/tracking | Add tracking event |
| GET | /vendor/shipments/{shipment_id}/tracking | Get tracking history |
| POST | /vendor/shipments/{shipment_id}/commit-inventory | Commit reserved stock |
| POST | /vendor/shipments/{shipment_id}/release-inventory | Release reserved stock |

### 2.15 Analytics

**Vendor router** — prefix=/vendors (shares namespace with Vendors module):

| Method | Path | Purpose |
|--------|------|---------|
| GET | /vendors/{vendor_id}/analytics | Vendor sales summary + top products + payout summary |
| GET | /vendors/{vendor_id}/payouts | List vendor payouts |

**Admin router** — prefix=/admin:

| Method | Path | Purpose |
|--------|------|---------|
| GET | /admin/analytics | Platform-wide metrics |
| POST | /admin/payouts/process | Process payouts (optional vendor_ids filter) |

### 2.16 System

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Health check |
| GET | /ready | Readiness check |
| GET | /docs | Swagger UI |
| GET | /redoc | ReDoc UI |
| GET | /openapi.json | OpenAPI schema |

### 2.17 Route Count Summary

| Module | Public | Vendor | Admin | Total |
|--------|--------|--------|-------|-------|
| Identity | 4 | 0 | 0 | 4 |
| Vendors | 2 | 0 | 3 | 5 |
| Storefronts | 3 | 5 | 0 | 8 |
| Catalog | 6 | 9 | 0 | 15 |
| Pricing | 2 | 0 | 4 | 6 |
| Inventory | 0 | 9 | 0 | 9 |
| Cart | 6 | 0 | 0 | 6 |
| Checkout | 4 | 0 | 0 | 4 |
| Orders | 4 | 4 | 0 | 8 |
| Payments | 4 | 1 | 0 | 5 |
| Webhooks | 4 | 0 | 0 | 4 |
| Promotions | 2 | 8 | 0 | 10 |
| Reviews | 5 | 0 | 1 | 6 |
| Customers | 6 | 0 | 0 | 6 |
| Fulfillment | 3 | 7 | 0 | 10 |
| Analytics | 2 | 0 | 2 | 4 |
| System | 5 | 0 | 0 | 5 |
| **Total** | **62** | **43** | **10** | **115** |

---

## 3. Critical Implementation Notes

### 3.1 CORS

The backend CORS is configured for `http://localhost:3000` and `http://localhost:8080`. If your Vite dev server runs on `5173` (default), either:
- Add `http://localhost:5173` to `CORS_ORIGINS` in `.env`, or
- Use a Vite proxy (recommended):

```ts
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
});
```

With the proxy, set `VITE_API_BASE_URL=http://localhost:5173/api` in `.env.local`.

### 3.2 Authentication

- All authenticated endpoints require `Authorization: Bearer <access_token>` header.
- The backend's `get_current_user` uses `Header(..., description="Bearer token")` — the header is **mandatory** (not optional) for protected routes.
- For routes that accept guest users (cart), the frontend must either send the Bearer token OR pass `?session_id=<uuid>` as a query param.
- Store the guest `session_id` (UUID v4) in `localStorage` on first visit and reuse across requests.
- On login, call `POST /cart/merge` to merge the guest cart into the authenticated user's cart.

### 3.3 Idempotency

- `POST /checkout` **requires** an `idempotency_key` field. Generate with `crypto.randomUUID()`.
- Store the key in `sessionStorage` for the duration of the checkout flow — if the user retries (network error, refresh), reuse the same key.
- Same pattern for `POST /payments/{order_id}/pay` and `POST /payments/{payment_id}/refund` (optional but recommended).

### 3.4 Route Collisions in Backend

The backend has intentional prefix collisions that affect frontend behavior:

1. **`/orders/*` is shared** between `orders.router` and `fulfillment.router`:
   - `POST /orders/{order_id}/ship` is registered in BOTH. Since fulfillment is registered after orders in `main.py`, the fulfillment version wins. Always use the fulfillment version (accepts `carrier` + `tracking_number` body).

2. **`/vendors/*` is shared** between `vendors.router` and `analytics.router`:
   - `/vendors/onboard` (Vendors) vs `/vendors/{vendor_id}/analytics` (Analytics). Path matching is unambiguous because `{vendor_id}` is an int path param.

3. **`/admin/*` is shared** between `pricing.admin_router`, `analytics.admin_router`, and `reviews.admin_router`. The `payments.admin_router` is **defined but never registered in `main.py`** — do not rely on admin payment routes.

### 3.5 Unusual Paths

- `GET /orders/{order_number}/number` — the literal word `number` is in the path. Your path builder should not strip it.
- `GET /vendor/inventory/` — trailing slash matters; use the bare path.

### 3.6 OpenAPI Type Generation

Once the backend is running (`uvicorn app.main:app --reload --port 8000`), generate TypeScript types:

```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.d.ts
```

Add this as an npm script:

```json
{
  "scripts": {
    "gen:api": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api.d.ts"
  }
}
```

This guarantees your TypeScript types match the live API exactly.

### 3.7 Error Response Shapes

The backend returns two error shapes. Your Axios interceptor must handle both:

**Domain errors** (from `app/core/exceptions.py`):

```json
{ "error": "Not found", "detail": "Vendor with identifier '5' was not found" }
```

**FastAPI validation errors** (422):

```json
{
  "detail": [
    { "loc": ["body", "email"], "msg": "field required", "type": "value_error.missing" }
  ]
}
```

HTTP status codes used: 400, 401, 403, 404, 409, 422, 500.

### 3.8 Enums to Mirror in TypeScript

| Enum | Values |
|------|--------|
| `UserRole` | customer, vendor, admin |
| `VendorStatus` | pending, verified, suspended |
| `OrderStatus` | pending, confirmed, processing, shipped, delivered, cancelled, refunded |
| `PaymentStatus` | pending, processing, completed, failed, refunded, partially_refunded |
| `ProductType` | simple, variable, bundle, subscription, digital |
| `PageType` | home, about, contact, custom |
| `DiscountType` | percentage, fixed (verify in `promotions/models.py`) |
| `LoyaltyTier` | bronze, silver, gold, platinum |
| `MovementType` | (verify in `inventory/models.py`) |
| `ShipmentStatus` | pending, label_created, picked_up, in_transit, out_for_delivery, delivered, returned, cancelled, failed |

---

## 4. Tech Stack & Architecture

### 4.1 Core Stack

| Layer | Tool | Rationale |
|-------|------|-----------|
| Build | Vite 5+ | Fast HMR, ESM-first |
| Framework | React 18 + TypeScript (strict) | Industry standard |
| Routing | React Router v6 (data routers) | Role-based loaders |
| Styling | Tailwind CSS 3.4 + shadcn/ui (Radix primitives) | Headless a11y, beautiful defaults |
| Server State | TanStack Query v5 | Caching, retries, optimistic updates |
| Client State | Zustand | Cart, UI, auth slices |
| Forms | React Hook Form + Zod | Schema-validated (mirrors Pydantic) |
| HTTP | Axios with interceptors | Centralized auth + error handling |
| Charts | Recharts | Analytics dashboards |
| Tables | TanStack Table v8 | Vendor/admin data grids |
| Icons | Lucide React | Tree-shakable, consistent |
| Toasts | Sonner | Non-blocking notifications |
| Payments UI | Stripe Elements / Paystack Inline / Flutterwave Rave / Monnify SDK | Gateway-aware |
| Testing | Vitest + React Testing Library + MSW | Unit/integration |
| E2E | Playwright | Critical paths |
| Lint/Format | ESLint (typescript-eslint) + Prettier | Consistency |
| Git hooks | Husky + lint-staged | Quality gate |

### 4.2 Architecture Principles

1. **Feature-based folders** over type-based folders
2. **Colocation** of components, hooks, and types
3. **Server state** in TanStack Query, **client state** in Zustand
4. **Type safety** end-to-end (OpenAPI -> Zod -> React Hook Form)
5. **Optimistic UI** for high-frequency mutations (cart, wishlist)
6. **Lazy loading** for all route components
7. **Code splitting** at the vendor/admin boundary

---

## 5. Project Structure

```
src/
├── app/                      # App-wide setup
│   ├── main.tsx
│   ├── App.tsx
│   ├── router.tsx            # All route definitions with role guards
│   └── providers.tsx         # Query, Auth, Theme, Toast providers
│
├── api/                      # API client
│   ├── client.ts             # Axios instance with interceptors
│   ├── endpoints/            # One file per module
│   │   ├── auth.ts
│   │   ├── vendors.ts
│   │   ├── storefronts.ts
│   │   ├── catalog.ts
│   │   ├── pricing.ts
│   │   ├── inventory.ts
│   │   ├── cart.ts
│   │   ├── checkout.ts
│   │   ├── orders.ts
│   │   ├── payments.ts
│   │   ├── promotions.ts
│   │   ├── reviews.ts
│   │   ├── customers.ts
│   │   ├── fulfillment.ts
│   │   └── analytics.ts
│   └── queries/              # TanStack Query hooks
│       ├── useProducts.ts
│       ├── useCart.ts
│       └── ...
│
├── components/
│   ├── ui/                   # shadcn primitives (Button, Input, Dialog, ...)
│   ├── layout/               # Header, Footer, Sidebar, Nav
│   ├── product/              # ProductCard, ProductGrid, ProductDetail
│   ├── cart/                 # CartDrawer, CartItem, CartSummary
│   ├── checkout/             # CheckoutSteps, AddressForm, PaymentSelector
│   ├── vendor/               # VendorDashboard widgets
│   └── admin/                # Admin widgets
│
├── features/                 # Feature-based modules
│   ├── auth/                 # LoginPage, RegisterPage, ProtectedRoute
│   ├── storefront/           # StoreLanding, StorePageRenderer
│   ├── catalog/              # ProductList, ProductDetail, SearchFilters
│   ├── cart/
│   ├── checkout/
│   ├── orders/               # Customer + Vendor order views
│   ├── payments/
│   ├── reviews/
│   ├── customers/            # Wishlist, Loyalty
│   ├── vendors/              # Onboarding, dashboard, store mgmt, products, inventory, analytics
│   ├── admin/                # Platform analytics, payouts, approvals
│   └── promotions/           # Coupon mgmt
│
├── lib/                      # Pure utilities
│   ├── formatters.ts         # currency, date, slug
│   ├── validators.ts         # Zod schemas (mirror API)
│   ├── errors.ts             # Error to UI mapping
│   └── idem.ts               # Idempotency key generator
│
├── stores/                   # Zustand slices
│   ├── authStore.ts
│   ├── cartStore.ts
│   ├── uiStore.ts
│   └── currencyStore.ts
│
├── types/                    # TS types mirroring OpenAPI
│   ├── api.d.ts
│   ├── domain.ts
│   └── enums.ts
│
├── styles/
│   ├── globals.css           # Tailwind directives
│   └── tokens.ts             # Design tokens
│
└── test/
    ├── setup.ts
    └── mocks/
```

---

## 6. UI/UX Design System

### 6.1 Design Principles

1. **Speed-first**: Optimistic UI, skeletons, prefetch on hover
2. **Trust signals**: Verified vendor badges, secure checkout badges, transparent pricing
3. **Mobile-first**: Touch targets >=44px, bottom-sheet cart, sticky checkout CTA
4. **Accessibility**: WCAG 2.1 AA, keyboard nav, focus rings, ARIA labels
5. **Internationalization-ready**: react-i18next with currency + locale aware formatting
6. **Dark mode**: Tailwind `class` strategy, persisted in `localStorage`

### 6.2 Visual Language

- **Color**: neutral grays + 1 brand accent (default indigo `#4F46E5`) + semantic (success/warn/error/info)
- **Typography**: Inter (UI) + Geist Mono (SKUs/IDs)
- **Spacing**: 4-pt grid (Tailwind defaults)
- **Radius**: `rounded-xl` (12px) for cards, `rounded-md` for inputs
- **Elevation**: layered shadows `shadow-sm/md/lg` + subtle borders
- **Motion**: 150-200ms ease-out, framer-motion for page transitions

### 6.3 Core Page Templates

1. **Storefront landing**: hero, featured collections carousel, brand strip
2. **PLP (Product Listing)**: left filter rail (desktop) / bottom-sheet (mobile), grid/list toggle, infinite scroll
3. **PDP (Product Detail)**: image gallery, variant selector, add-on matrix, price breakdown, reviews, related products
4. **Cart**: slide-over drawer + full page, promo code input, savings callouts
5. **Checkout**: 3-step wizard (Address -> Shipping/Review -> Payment)
6. **Order confirmation**: animated success, order timeline, cross-sell
7. **Account**: tabs for Profile, Orders, Wishlist, Loyalty, Addresses
8. **Vendor dashboard**: left sidebar nav, KPI cards, recent orders table, low-stock alerts
9. **Vendor product editor**: multi-step form with live preview
10. **Admin console**: global nav, dense data tables, bulk actions, modals

---

## 7. State Management Strategy

### 7.1 Server State (TanStack Query)

- **Query keys** are typed and hierarchical: `['products', 'list', { filters }]`, `['cart', userId]`
- **Default staleTime**: 30s; **gcTime**: 5min
- **Retry**: 3x with exponential backoff, skip 4xx (except 408/429)
- **Optimistic updates** for: cart add/update/remove, wishlist toggle
- **Infinite queries** for: search results, orders list, reviews
- **Prefetch** on hover for product cards

### 7.2 Client State (Zustand)

- **authStore**: `user, role, tokens, login(), logout(), refresh()`
- **cartStore**: minimal — only the `sessionId` for guest carts + sync trigger
- **uiStore**: theme, sidebar open, currency code, locale
- **currencyStore**: active currency, list from `/pricing/currencies`

### 7.3 Cart Sync Flow (Hybrid Auth)

1. On app load: generate/retrieve `sessionId` (UUID in `localStorage`)
2. All cart requests include `sessionId` query param if unauthenticated
3. On login: `POST /cart/merge` to merge guest cart into user cart
4. Cart state sourced from `/cart` GET, mutated via TanStack mutations -> invalidate `['cart']`

---

## 8. Authentication & Authorization

### 8.1 Token Strategy

- Store `access_token` + `refresh_token` in **memory** (Zustand) + mirrored in `httpOnly` cookies via a tiny `/auth/set-cookie` proxy endpoint (or accept `localStorage` if simpler; document the trade-off).
- Axios interceptor:
  - Attach `Authorization: Bearer <token>` to all requests
  - On 401, attempt `POST /auth/refresh` once, retry original request
  - On refresh failure -> clear store, redirect to `/login?returnTo=...`
- `idempotency_key` generated via `crypto.randomUUID()` for checkout, payments, refunds

### 8.2 Route Guards

- `<ProtectedRoute roles={['vendor','admin']}>` wraps role-gated pages
- Redirect logic:
  - Unauthenticated -> `/login?returnTo=<path>`
  - Wrong role -> `/forbidden` with explanation
- Public routes: storefront, products, search, vendor public profiles
- Vendor routes: prefixed `/vendor/*`, role=`vendor` or `admin`
- Admin routes: prefixed `/admin/*`, role=`admin` only

### 8.3 Onboarding Wizard (Vendors)

Multi-step: `Account -> Store Basics -> Branding (theme) -> First Product (skip) -> Done`
Calls `POST /vendors/onboard` once with collected payload.

---

## 9. Customer-Facing Flows

### 9.1 Browse & Discover

- **Home**: hero, trending products (search with `sort_by=popularity`), top stores, categories grid
- **Search**: debounced (300ms), `recent searches` in `localStorage`, suggestion dropdown
- **Filters**: category, brand, price range (dual slider), in-stock toggle, rating
- **Sort**: Newest, Price ascending/descending, Top rated, Best selling

### 9.2 Product Detail

- **Gallery**: thumbnails + main image, zoom on hover, swipe on mobile
- **Variants**: pill buttons (size/color); out-of-stock variants disabled
- **Addons**: grouped with min/max selection rules from `AddonGroup`
- **Price block**: resolved via `GET /pricing/{id}` showing `PriceBreakdown` (base, variant delta, addons, tax estimate)
- **Reviews**: rating summary histogram, filter by stars, "verified purchase" badge
- **Sticky ATC bar** on mobile: price + quantity + "Add to cart"

### 9.3 Cart & Checkout

- **Cart drawer** slides in from right; updates quantity inline; shows running total
- **Checkout** wizard:
  1. **Address** (with country select -> triggers `/checkout/calculate-shipping` & `/checkout/calculate-tax`)
  2. **Shipping method** (from shipping calculation result)
  3. **Payment** (gateway selector: Stripe / Paystack / Flutterwave / Monnify based on user region/gateway availability)
  4. **Place order** -> `POST /checkout` with `idempotency_key` -> redirect to confirmation
- **Error handling**: show field-level errors from 422 responses; global toast for system errors

### 9.4 Post-Purchase

- **Order tracking page**: live status timeline (pending -> confirmed -> processing -> shipped -> delivered), shipment tracking events polled every 30s
- **Reorder** button on delivered orders
- **Review prompt** on delivered orders (modal after 7 days)

---

## 10. Vendor Dashboard

### 10.1 Layout

- **Sidebar**: Dashboard, Products, Inventory, Orders, Promotions, Customers, Analytics, Storefront, Settings
- **Top bar**: store switcher (if multi-store), notifications, quick add product
- **Main**: data-dense but breathable

### 10.2 Key Screens

1. **Dashboard**: KPI cards (revenue today/7d/30d, AOV, conversion), low-stock alerts, recent orders
2. **Products**: table with bulk actions (activate/deactivate/delete), filters, CSV import
   - **Editor**: tabbed (General / Variants / Attributes / Images / Addons / SEO)
   - **Image manager**: drag-drop reorder, set primary
3. **Inventory**: location switcher, stock grid, adjust modal, reservation list, movement audit log
4. **Orders**: filterable table, detail drawer with fulfillment actions
   - **Create shipment**: carrier + tracking -> status updates
5. **Promotions**: coupons / promotions / gift cards tabs with usage stats
6. **Storefront**: theme customizer (color picker, font picker, layout preview), page builder
7. **Analytics**: sales over time, top products, payout history, customer cohorts

### 10.3 Inventory Operations UX

- **Adjust modal**: +/- quantity with reason code, reference link
- **Bulk adjust**: select multiple items, apply delta
- **Low-stock dashboard**: red badge for items below threshold, one-click reorder email

---

## 11. Admin Console

### 11.1 Layout

- **Global nav**: Dashboard, Vendors, Products, Orders, Payments, Currencies, Reviews, Payouts
- **Dense data tables** with column filters, sorting, pagination
- **Bulk actions**: approve, suspend, export
- **Detail drawers** for entity inspection

### 11.2 Key Screens

1. **Platform analytics**: revenue chart, top vendors, top products, customer growth
2. **Vendor management**: list with status filter, approve/suspend action
3. **Review moderation**: queue of pending reviews, approve/reject
4. **Currency management**: create/edit currencies, trigger exchange rate update
5. **Payout processing**: select period, run batch payout, view results

---

## 12. TypeScript Types & Enums

### 12.1 Recommended Zod Schemas (Mirror Pydantic)

Create `src/lib/validators.ts` with schemas that match the backend Pydantic models. This enables runtime validation in addition to compile-time types.

### 12.2 Key Enums (TypeScript constants)

```ts
// src/types/enums.ts
export const UserRole = {
  CUSTOMER: 'customer',
  VENDOR: 'vendor',
  ADMIN: 'admin',
} as const;
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const OrderStatus = {
  PENDING: 'pending',
  CONFIRMED: 'confirmed',
  PROCESSING: 'processing',
  SHIPPED: 'shipped',
  DELIVERED: 'delivered',
  CANCELLED: 'cancelled',
  REFUNDED: 'refunded',
} as const;
export type OrderStatus = (typeof OrderStatus)[keyof typeof OrderStatus];

export const PaymentStatus = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  REFUNDED: 'refunded',
  PARTIALLY_REFUNDED: 'partially_refunded',
} as const;
export type PaymentStatus = (typeof PaymentStatus)[keyof typeof PaymentStatus];

export const ShipmentStatus = {
  PENDING: 'pending',
  LABEL_CREATED: 'label_created',
  PICKED_UP: 'picked_up',
  IN_TRANSIT: 'in_transit',
  OUT_FOR_DELIVERY: 'out_for_delivery',
  DELIVERED: 'delivered',
  RETURNED: 'returned',
  CANCELLED: 'cancelled',
  FAILED: 'failed',
} as const;
export type ShipmentStatus = (typeof ShipmentStatus)[keyof typeof ShipmentStatus];

export const LoyaltyTier = {
  BRONZE: 'bronze',
  SILVER: 'silver',
  GOLD: 'gold',
  PLATINUM: 'platinum',
} as const;
export type LoyaltyTier = (typeof LoyaltyTier)[keyof typeof LoyaltyTier];
```

---

## 13. Error Handling Contract

### 13.1 Axios Interceptor

```ts
// src/api/client.ts
import axios, { AxiosError } from 'axios';
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'sonner';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
});

// Request: attach token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response: handle 401 with refresh
let isRefreshing = false;
api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError<ApiError>) => {
    const original = error.config!;
    if (error.response?.status === 401 && !original._retry) {
      if (isRefreshing) return Promise.reject(error);
      isRefreshing = true;
      original._retry = true;
      try {
        await useAuthStore.getState().refresh();
        original.headers!.Authorization = `Bearer ${useAuthStore.getState().accessToken}`;
        return api(original);
      } catch {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      } finally {
        isRefreshing = false;
      }
    }

    // Normalize error
    const message =
      error.response?.data?.detail ||
      error.response?.data?.error ||
      error.message ||
      'Something went wrong';
    toast.error(message);
    return Promise.reject(error);
  }
);
```

### 13.2 Error Type Guard

```ts
type ApiError = {
  error?: string;
  detail?: string | Array<{ loc: string[]; msg: string; type: string }>;
};
```

---

## 14. Implementation Roadmap

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | Foundation | Vite + TS + Tailwind + shadcn/ui setup, Axios client, error handling, route guards, auth pages (login/register/me), TanStack Query providers, OpenAPI type generation script |
| 2 | Public Storefront | Home, store list, store detail (theme rendering), product list (PLP), product detail (PDP), search, categories, brands |
| 3 | Cart & Pricing | Cart drawer + page, session-id guest flow, cart merge on login, price resolution on PDP, currency selector |
| 4 | Checkout & Payments | 3-step checkout wizard, address form, shipping/tax calculators, coupon application, gateway routing (Stripe/Paystack/Flutterwave/Monnify), idempotency, order confirmation |
| 5 | Customer Account | Profile, order history, order detail with tracking, wishlist, loyalty dashboard, address book |
| 6 | Reviews & Engagement | Review submission, rating histograms, review moderation (admin), helpful votes |
| 7 | Vendor Onboarding | Multi-step wizard hitting `/vendors/onboard`, store setup, theme editor, page builder |
| 8 | Vendor Catalog | Product list, product editor (variants/attributes/images/addons), bulk actions, CSV import |
| 9 | Vendor Inventory & Orders | Location mgmt, stock grid, adjustments, reservations, order list, shipment creation, tracking timeline |
| 10 | Vendor Promotions & Analytics | Coupons/promotions/gift cards CRUD, sales dashboard with charts, payout history |
| 11 | Admin Console | Platform analytics, vendor approval, payout processing, currency/exchange-rate mgmt, review approval |
| 12 | Polish & Launch | E2E tests, performance audit, accessibility audit, error boundaries, SEO, analytics integration, deployment |

---

## 15. Local Development Setup

### 15.1 Prerequisites

1. Backend running on `http://localhost:8000`:
   ```bash
   cd marketforge-api-ecom
   docker-compose up -d            # PostgreSQL + Redis
   alembic upgrade head            # Run migrations
   uvicorn app.main:app --reload --port 8000
   ```

2. Verify backend: visit `http://localhost:8000/docs` (Swagger UI should load)

### 15.2 Frontend Bootstrap

```bash
npm create vite@latest marketforge-web -- --template react-ts
cd marketforge-web
npm install

# Core deps
npm install react-router-dom @tanstack/react-query zustand axios
npm install react-hook-form zod @hookform/resolvers
npm install tailwindcss postcss autoprefixer
npm install lucide-react sonner clsx tailwind-merge class-variance-authority
npm install recharts @tanstack/react-table
npm install @stripe/stripe-js @stripe/react-stripe-js

# Dev deps
npm install -D @types/node vitest @testing-library/react @testing-library/jest-dom jsdom
npm install -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
npm install -D prettier eslint-config-prettier
npm install -D msw openapi-typescript
npx tailwindcss init -p
```

### 15.3 Environment Variables

Create `.env.local`:

```env
VITE_API_BASE_URL=http://localhost:5173/api
VITE_APP_NAME=MarketForge
```

With the Vite proxy forwarding `/api/*` -> `http://localhost:8000/*`.

### 15.4 First Steps

1. **Start backend**, then run:
   ```bash
   npm run gen:api
   ```
   This generates `src/types/api.d.ts` from the live OpenAPI schema.

2. **Set up shadcn/ui**:
   ```bash
   npx shadcn-ui@latest init
   npx shadcn-ui@latest add button input dialog dropdown-menu sheet toast
   ```

3. **Set up MSW for local development without backend** (optional):
   ```bash
   npx msw init public/ --save
   ```
   Create handlers that return mock data for each endpoint.

4. **First commit**:
   ```bash
   git init
   git add .
   git commit -m "chore: initial Vite + React + TS + Tailwind setup"
   ```

### 15.5 Verification Checklist

- [ ] `npm run dev` starts on `http://localhost:5173`
- [ ] `http://localhost:5173/api/health` returns `{"status":"healthy"}` (proxied)
- [ ] `http://localhost:8000/docs` shows all 115 endpoints
- [ ] `npm run gen:api` produces `src/types/api.d.ts` with no errors
- [ ] Login form posts to `/auth/login` and stores tokens
- [ ] Protected route redirects unauthenticated users to `/login`

---

## Appendix A: Complete Endpoint Reference (Quick Lookup)

```
# Auth
POST   /auth/register
POST   /auth/login
POST   /auth/refresh
GET    /auth/me

# Vendors
POST   /vendors/onboard
GET    /vendors/{vendor_id}
PATCH  /vendors/{vendor_id}
PATCH  /vendors/{vendor_id}/status
GET    /vendors/me/profile

# Storefronts (public)
GET    /stores
GET    /stores/{slug}
GET    /stores/{store_slug}/pages/{page_slug}

# Storefronts (vendor)
POST   /vendor/stores
PATCH  /vendor/stores/{store_id}
POST   /vendor/stores/{store_id}/theme
POST   /vendor/stores/{store_id}/pages
PATCH  /vendor/stores/{store_id}/pages/{page_id}

# Catalog (public)
GET    /stores/{store_slug}/products
GET    /stores/{store_slug}/products/{product_slug}
GET    /stores/{store_slug}/collections
GET    /products/search
GET    /categories
GET    /brands

# Catalog (vendor)
POST   /vendor/products
PATCH  /vendor/products/{product_id}
DELETE /vendor/products/{product_id}
POST   /vendor/products/{product_id}/variants
PATCH  /vendor/products/{product_id}/variants/{variant_id}
POST   /vendor/products/{product_id}/attributes
POST   /vendor/products/{product_id}/images
POST   /vendor/products/{product_id}/addon-groups
POST   /vendor/addon-groups/{group_id}/addons

# Pricing (public)
GET    /pricing/{product_id}
GET    /pricing/currencies

# Pricing (admin)
GET    /admin/exchange-rates
POST   /admin/currencies
PATCH  /admin/currencies/{currency_id}
POST   /admin/exchange-rates/update

# Inventory (vendor)
GET    /vendor/inventory/locations
POST   /vendor/inventory/locations
PATCH  /vendor/inventory/locations/{location_id}
GET    /vendor/inventory/
POST   /vendor/inventory/adjust
POST   /vendor/inventory/reserve
POST   /vendor/inventory/release
GET    /vendor/inventory/low-stock
GET    /vendor/inventory/movements

# Cart
GET    /cart
POST   /cart/items
PATCH  /cart/items/{item_id}
DELETE /cart/items/{item_id}
POST   /cart/merge
DELETE /cart

# Checkout
POST   /checkout
POST   /checkout/apply-coupon
GET    /checkout/calculate-shipping
GET    /checkout/calculate-tax

# Orders (customer)
GET    /orders
GET    /orders/{order_id}
GET    /orders/{order_number}/number
POST   /orders/{order_id}/cancel

# Orders (vendor)
GET    /vendor/orders
POST   /vendor/orders/{order_id}/ship
PATCH  /vendor/orders/shipments/{shipment_id}
GET    /vendor/orders/{order_id}/shipments

# Payments (customer)
POST   /payments/webhook
GET    /payments/{payment_id}
POST   /payments/{payment_id}/refund
POST   /payments/{order_id}/pay

# Payments (vendor)
GET    /vendor/payments

# Webhooks
POST   /webhooks/stripe
POST   /webhooks/paystack
POST   /webhooks/flutterwave
POST   /webhooks/monnify

# Promotions (public)
POST   /validate-coupon
POST   /validate-gift-card

# Promotions (vendor)
POST   /vendor/coupons
GET    /vendor/coupons
PATCH  /vendor/coupons/{coupon_id}
POST   /vendor/promotions
GET    /vendor/promotions
PATCH  /vendor/promotions/{promotion_id}
POST   /vendor/gift-cards
GET    /vendor/gift-cards

# Reviews (public)
POST   /products/{product_id}/reviews
GET    /products/{product_id}/reviews
GET    /products/{product_id}/rating
PATCH  /products/reviews/{review_id}
DELETE /products/reviews/{review_id}

# Reviews (admin)
POST   /admin/reviews/{review_id}/approve

# Customers
POST   /customers/wishlist/{product_id}
DELETE /customers/wishlist/{product_id}
GET    /customers/wishlist
GET    /customers/loyalty
POST   /customers/loyalty/redeem
GET    /customers/loyalty/tiers

# Fulfillment (public)
GET    /orders/{order_id}/shipments
GET    /orders/{order_id}/shipments/{shipment_id}
POST   /orders/{order_id}/ship

# Fulfillment (vendor)
POST   /vendor/orders/{order_id}/ship
PATCH  /vendor/shipments/{shipment_id}
PATCH  /vendor/shipments/{shipment_id}/status
POST   /vendor/shipments/{shipment_id}/tracking
GET    /vendor/shipments/{shipment_id}/tracking
POST   /vendor/shipments/{shipment_id}/commit-inventory
POST   /vendor/shipments/{shipment_id}/release-inventory

# Analytics (vendor)
GET    /vendors/{vendor_id}/analytics
GET    /vendors/{vendor_id}/payouts

# Analytics (admin)
GET    /admin/analytics
POST   /admin/payouts/process

# System
GET    /health
GET    /ready
GET    /docs
GET    /redoc
GET    /openapi.json
```

---

## Appendix B: Frontend Route Map

Map frontend routes to backend endpoints:

| Frontend Route | Backend Endpoints Used |
|----------------|------------------------|
| `/` | `GET /products/search?sort_by=popularity`, `GET /stores` |
| `/stores` | `GET /stores` |
| `/stores/:slug` | `GET /stores/{slug}`, `GET /stores/{slug}/products` |
| `/stores/:slug/products/:productSlug` | `GET /stores/{slug}/products/{productSlug}`, `GET /pricing/{id}`, `GET /products/{id}/reviews`, `GET /products/{id}/rating` |
| `/search` | `GET /products/search`, `GET /categories`, `GET /brands` |
| `/cart` | `GET /cart`, `PATCH /cart/items/{id}`, `DELETE /cart/items/{id}` |
| `/checkout` | `GET /cart`, `POST /checkout/apply-coupon`, `GET /checkout/calculate-shipping`, `GET /checkout/calculate-tax`, `POST /checkout` |
| `/checkout/success` | `GET /orders/{order_id}` |
| `/login` | `POST /auth/login` |
| `/register` | `POST /auth/register` |
| `/account` | `GET /auth/me` |
| `/account/orders` | `GET /orders` |
| `/account/orders/:id` | `GET /orders/{id}` |
| `/account/wishlist` | `GET /customers/wishlist`, `POST /customers/wishlist/{id}`, `DELETE /customers/wishlist/{id}` |
| `/account/loyalty` | `GET /customers/loyalty`, `GET /customers/loyalty/tiers` |
| `/vendor/onboard` | `POST /vendors/onboard` |
| `/vendor` | `GET /vendors/me/profile` |
| `/vendor/products` | `GET /vendor/products/*` (catalog), `POST /vendor/products`, etc. |
| `/vendor/inventory` | `GET /vendor/inventory/*` |
| `/vendor/orders` | `GET /vendor/orders` |
| `/vendor/orders/:id` | `GET /vendor/orders/{id}/shipments`, `POST /vendor/orders/{id}/ship` |
| `/vendor/promotions` | `GET /vendor/coupons`, `GET /vendor/promotions`, `GET /vendor/gift-cards` |
| `/vendor/analytics` | `GET /vendors/{vendor_id}/analytics`, `GET /vendors/{vendor_id}/payouts` |
| `/vendor/storefront` | `GET /vendor/stores/*`, `POST /vendor/stores/{id}/theme`, etc. |
| `/admin` | `GET /admin/analytics` |
| `/admin/vendors` | `GET /vendors/*`, `PATCH /vendors/{id}/status` |
| `/admin/currencies` | `GET /pricing/currencies`, `POST /admin/currencies`, `PATCH /admin/currencies/{id}` |
| `/admin/reviews` | `GET /products/{id}/reviews?is_approved=false`, `POST /admin/reviews/{id}/approve` |
| `/admin/payouts` | `POST /admin/payouts/process` |

---

**Document version**: 1.0
**Backend version**: 0.1.0
**Total endpoints documented**: 115
**Last updated**: 2026-06-09
