from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import redis_client
from app.core.exceptions import (
    MarketForgeException,
    marketforge_exception_handler,
    generic_exception_handler,
)
from app.core.logging import setup_logging, get_logger
from app.modules.identity.router import router as identity_router
from app.modules.vendors.router import router as vendor_router
from app.modules.storefronts.router import router as storefront_router
from app.modules.storefronts.router import vendor_router as store_vendor_router
from app.modules.catalog.router import router as catalog_router
from app.modules.catalog.router import vendor_router as catalog_vendor_router
from app.modules.pricing.router import router as pricing_router
from app.modules.pricing.router import admin_router as pricing_admin_router
from app.modules.inventory.router import vendor_router as inventory_vendor_router
from app.modules.cart.router import router as cart_router
from app.modules.orders.router import router as orders_router
from app.modules.orders.router import vendor_router as orders_vendor_router
from app.modules.checkout.router import router as checkout_router
from app.modules.payments.router import router as payments_router
from app.modules.payments.router import vendor_router as payments_vendor_router
from app.modules.promotions.router import router as promotions_router
from app.modules.promotions.router import vendor_router as promotions_vendor_router
from app.modules.reviews.router import router as reviews_router
from app.modules.reviews.router import admin_router as reviews_admin_router
from app.modules.customers.router import router as customers_router
from app.modules.fulfillment.router import router as fulfillment_router
from app.modules.fulfillment.router import vendor_router as fulfillment_vendor_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger = get_logger("startup")
    logger.info("Starting MarketForge API", version="0.1.0")

    await init_db()
    logger.info("Database initialized")

    await redis_client.connect()
    logger.info("Redis connected")

    yield

    logger.info("Shutting down MarketForge API")
    await redis_client.disconnect()
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="MarketForge API",
        description="Multi-vendor commerce platform API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(MarketForgeException, marketforge_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(identity_router)
    app.include_router(vendor_router)
    app.include_router(storefront_router)
    app.include_router(store_vendor_router)
    app.include_router(catalog_router)
    app.include_router(catalog_vendor_router)
    app.include_router(pricing_router)
    app.include_router(pricing_admin_router)
    app.include_router(inventory_vendor_router)
    app.include_router(cart_router)
    app.include_router(orders_router)
    app.include_router(orders_vendor_router)
    app.include_router(checkout_router)
    app.include_router(payments_router)
    app.include_router(payments_vendor_router)
    app.include_router(promotions_router)
    app.include_router(promotions_vendor_router)
    app.include_router(reviews_router)
    app.include_router(reviews_admin_router)
    app.include_router(customers_router)
    app.include_router(fulfillment_router)
    app.include_router(fulfillment_vendor_router)

    @app.get("/health")
    async def health_check() -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={"status": "healthy", "service": "marketforge-api"},
        )

    @app.get("/ready")
    async def readiness_check() -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={"status": "ready"},
        )

    return app


app = create_app()