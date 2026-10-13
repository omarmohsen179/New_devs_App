from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.core.database_pool import db_pool


async def _get_session():
    await db_pool.initialize()
    if not db_pool.session_factory:
        raise Exception("Database pool not available")
    return db_pool.get_session()


async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Dict[str, Any]:
    """
    Calculates revenue for a specific month.
    """
    async with await _get_session() as session:
        tz_row = (await session.execute(
            text("SELECT timezone FROM properties WHERE id = :property_id AND tenant_id = :tenant_id"),
            {"property_id": property_id, "tenant_id": tenant_id},
        )).fetchone()
        tz = ZoneInfo(tz_row.timezone if tz_row else "UTC")

        # month boundaries in the property's local time
        start_date = datetime(year, month, 1, tzinfo=tz)
        end_date = datetime(year + 1, 1, 1, tzinfo=tz) if month == 12 else datetime(year, month + 1, 1, tzinfo=tz)

        row = (await session.execute(text("""
            SELECT COALESCE(SUM(total_amount), 0) AS total, COUNT(*) AS reservation_count
            FROM reservations
            WHERE property_id = :property_id
            AND tenant_id = :tenant_id
            AND check_in_date >= :start_date
            AND check_in_date < :end_date
        """), {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": start_date,
            "end_date": end_date,
        })).fetchone()

        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": str(Decimal(str(row.total))),
            "currency": "USD",
            "count": row.reservation_count,
        }


async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    async with await _get_session() as session:
        row = (await session.execute(text("""
            SELECT
                COALESCE(SUM(total_amount), 0) AS total_revenue,
                COUNT(*) AS reservation_count
            FROM reservations
            WHERE property_id = :property_id AND tenant_id = :tenant_id
        """), {
            "property_id": property_id,
            "tenant_id": tenant_id,
        })).fetchone()

        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": str(Decimal(str(row.total_revenue))),
            "currency": "USD",
            "count": row.reservation_count,
        }


async def list_properties(tenant_id: str) -> List[Dict[str, Any]]:
    async with await _get_session() as session:
        rows = (await session.execute(
            text("SELECT id, name, timezone FROM properties WHERE tenant_id = :tenant_id ORDER BY id"),
            {"tenant_id": tenant_id},
        )).fetchall()
        return [{"id": r.id, "name": r.name, "timezone": r.timezone} for r in rows]
