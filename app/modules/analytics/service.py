from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.analytics.models import VendorPayout, PayoutStatus
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.storefronts.models import Store
from app.modules.vendors.models import Vendor
from app.modules.catalog.models import Product
from app.modules.identity.models import User


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_vendor_sales_summary(
        self,
        vendor_id: int,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Any]:
        vendor = await self.db.execute(
            select(Vendor).where(Vendor.id == vendor_id)
        )
        vendor = vendor.scalar_one_or_none()
        if not vendor:
            raise NotFoundError("Vendor", str(vendor_id))

        store_ids_query = await self.db.execute(
            select(Store.id).where(Store.vendor_id == vendor_id)
        )
        store_ids = [s[0] for s in store_ids_query.fetchall()]

        if not store_ids:
            return {
                "total_revenue": 0.0,
                "total_orders": 0,
                "average_order_value": 0.0,
                "period_start": period_start,
                "period_end": period_end,
            }

        result = await self.db.execute(
            select(
                func.coalesce(func.sum(Order.total), 0).label("total_revenue"),
                func.count(Order.id).label("total_orders"),
            ).where(
                and_(
                    Order.store_id.in_(store_ids),
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED]),
                    Order.created_at >= period_start,
                    Order.created_at <= period_end,
                )
            )
        )
        row = result.one()
        total_revenue = float(row.total_revenue or 0)
        total_orders = int(row.total_orders or 0)

        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "average_order_value": total_revenue / total_orders if total_orders > 0 else 0.0,
            "period_start": period_start,
            "period_end": period_end,
        }

    async def get_vendor_top_products(
        self,
        vendor_id: int,
        period_start: datetime,
        period_end: datetime,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        store_ids_query = await self.db.execute(
            select(Store.id).where(Store.vendor_id == vendor_id)
        )
        store_ids = [s[0] for s in store_ids_query.fetchall()]

        if not store_ids:
            return []

        result = await self.db.execute(
            select(
                OrderItem.product_id,
                OrderItem.name,
                func.sum(OrderItem.quantity).label("units_sold"),
                func.sum(OrderItem.total_price).label("revenue"),
            ).join(Order, OrderItem.order_id == Order.id).where(
                and_(
                    Order.store_id.in_(store_ids),
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED]),
                    Order.created_at >= period_start,
                    Order.created_at <= period_end,
                )
            ).group_by(
                OrderItem.product_id, OrderItem.name
            ).order_by(
                func.sum(OrderItem.quantity).desc()
            ).limit(limit)
        )

        return [
            {
                "product_id": row.product_id,
                "product_name": row.name,
                "units_sold": int(row.units_sold or 0),
                "revenue": float(row.revenue or 0),
            }
            for row in result.all()
        ]

    async def get_vendor_analytics(
        self,
        vendor_id: int,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        if not period_end:
            period_end = datetime.utcnow()
        if not period_start:
            period_start = period_end - timedelta(days=30)

        sales_summary = await self.get_vendor_sales_summary(vendor_id, period_start, period_end)
        top_products = await self.get_vendor_top_products(vendor_id, period_start, period_end)

        payouts_result = await self.db.execute(
            select(
                func.count(VendorPayout.id).label("total"),
                func.coalesce(func.sum(VendorPayout.amount), 0).label("total_paid"),
            ).where(
                and_(
                    VendorPayout.vendor_id == vendor_id,
                    VendorPayout.status == PayoutStatus.COMPLETED,
                )
            )
        )
        payouts_row = payouts_result.one()

        return {
            "vendor_id": vendor_id,
            "period_start": period_start,
            "period_end": period_end,
            "sales_summary": sales_summary,
            "top_products": top_products,
            "payout_summary": {
                "total_payouts": int(payouts_row.total or 0),
                "total_paid": float(payouts_row.total_paid or 0),
            },
        }

    async def get_platform_analytics(
        self,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        if not period_end:
            period_end = datetime.utcnow()
        if not period_start:
            period_start = period_end - timedelta(days=30)

        total_revenue_result = await self.db.execute(
            select(
                func.coalesce(func.sum(Order.total), 0).label("total_revenue"),
                func.count(Order.id).label("total_orders"),
            ).where(
                and_(
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED]),
                    Order.created_at >= period_start,
                    Order.created_at <= period_end,
                )
            )
        )
        revenue_row = total_revenue_result.one()
        total_revenue = float(revenue_row.total_revenue or 0)
        total_orders = int(revenue_row.total_orders or 0)

        total_vendors_result = await self.db.execute(select(func.count(Vendor.id)))
        total_vendors = int(total_vendors_result.scalar() or 0)

        total_products_result = await self.db.execute(select(func.count(Product.id)))
        total_products = int(total_products_result.scalar() or 0)

        total_customers_result = await self.db.execute(
            select(func.count(User.id)).where(User.role == "customer")
        )
        total_customers = int(total_customers_result.scalar() or 0)

        revenue_by_day_result = await self.db.execute(
            select(
                func.date(Order.created_at).label("day"),
                func.sum(Order.total).label("revenue"),
                func.count(Order.id).label("orders"),
            ).where(
                and_(
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED]),
                    Order.created_at >= period_start,
                    Order.created_at <= period_end,
                )
            ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at))
        )
        revenue_by_day = [
            {"day": str(row.day), "revenue": float(row.revenue), "orders": int(row.orders)}
            for row in revenue_by_day_result.all()
        ]

        top_vendors_result = await self.db.execute(
            select(
                Vendor.id,
                Vendor.name,
                func.sum(Order.total).label("revenue"),
            ).join(Store, Vendor.id == Store.vendor_id).join(Order, Store.id == Order.store_id).where(
                and_(
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED]),
                    Order.created_at >= period_start,
                    Order.created_at <= period_end,
                )
            ).group_by(Vendor.id, Vendor.name).order_by(func.sum(Order.total).desc()).limit(10)
        )
        top_vendors = [
            {"vendor_id": row.id, "vendor_name": row.name, "revenue": float(row.revenue)}
            for row in top_vendors_result.all()
        ]

        top_products_result = await self.db.execute(
            select(
                OrderItem.product_id,
                OrderItem.name,
                func.sum(OrderItem.quantity).label("units_sold"),
                func.sum(OrderItem.total_price).label("revenue"),
            ).join(Order, OrderItem.order_id == Order.id).where(
                and_(
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED]),
                    Order.created_at >= period_start,
                    Order.created_at <= period_end,
                )
            ).group_by(
                OrderItem.product_id, OrderItem.name
            ).order_by(
                func.sum(OrderItem.quantity).desc()
            ).limit(10)
        )
        top_products = [
            {
                "product_id": row.product_id,
                "product_name": row.name,
                "units_sold": int(row.units_sold or 0),
                "revenue": float(row.revenue or 0),
            }
            for row in top_products_result.all()
        ]

        return {
            "period_start": period_start,
            "period_end": period_end,
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_vendors": total_vendors,
            "total_products": total_products,
            "total_customers": total_customers,
            "average_order_value": total_revenue / total_orders if total_orders > 0 else 0.0,
            "revenue_by_day": revenue_by_day,
            "top_vendors": top_vendors,
            "top_products": top_products,
        }

    async def get_vendor_payouts(
        self,
        vendor_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[VendorPayout], int]:
        count_result = await self.db.execute(
            select(func.count(VendorPayout.id)).where(VendorPayout.vendor_id == vendor_id)
        )
        total = int(count_result.scalar() or 0)

        result = await self.db.execute(
            select(VendorPayout)
            .where(VendorPayout.vendor_id == vendor_id)
            .order_by(VendorPayout.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        payouts = list(result.scalars().all())
        return payouts, total

    async def generate_payout(
        self,
        vendor_id: int,
        period_start: datetime,
        period_end: datetime,
    ) -> VendorPayout:
        vendor = await self.db.execute(
            select(Vendor).where(Vendor.id == vendor_id)
        )
        vendor = vendor.scalar_one_or_none()
        if not vendor:
            raise NotFoundError("Vendor", str(vendor_id))

        sales_summary = await self.get_vendor_sales_summary(vendor_id, period_start, period_end)
        total_sales = sales_summary["total_revenue"]
        commission_amount = total_sales * vendor.commission_rate
        payout_amount = total_sales - commission_amount

        existing = await self.db.execute(
            select(VendorPayout).where(
                and_(
                    VendorPayout.vendor_id == vendor_id,
                    VendorPayout.period_start == period_start,
                    VendorPayout.period_end == period_end,
                )
            )
        )
        existing_payout = existing.scalar_one_or_none()
        if existing_payout:
            raise ValidationError(f"Payout already exists for vendor {vendor_id} in this period")

        payout = VendorPayout(
            vendor_id=vendor_id,
            amount=payout_amount,
            currency_code="USD",
            status=PayoutStatus.PENDING,
            period_start=period_start,
            period_end=period_end,
            total_sales=total_sales,
            total_orders=sales_summary["total_orders"],
            commission_amount=commission_amount,
        )
        self.db.add(payout)
        await self.db.flush()
        await self.db.refresh(payout)
        return payout

    async def process_payouts(
        self,
        vendor_ids: Optional[List[int]] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> List[VendorPayout]:
        if not period_end:
            period_end = datetime.utcnow()
        if not period_start:
            period_start = period_end - timedelta(days=30)

        if vendor_ids is None:
            vendor_result = await self.db.execute(select(Vendor.id))
            vendor_ids = [v[0] for v in vendor_result.fetchall()]

        processed_payouts = []
        for vendor_id in vendor_ids:
            try:
                payout = await self.generate_payout(vendor_id, period_start, period_end)
                payout.status = PayoutStatus.PROCESSING
                await self.db.flush()
                payout.status = PayoutStatus.COMPLETED
                payout.processed_at = datetime.utcnow()
                await self.db.flush()
                processed_payouts.append(payout)
            except Exception:
                continue

        return processed_payouts