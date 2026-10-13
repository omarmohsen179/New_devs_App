from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from app.services.cache import get_revenue_summary
from app.services.reservations import list_properties
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()


def _tenant_id(current_user) -> str:
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant associated with user")
    return tenant_id


@router.get("/dashboard/properties")
async def get_dashboard_properties(
    current_user: dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    return await list_properties(_tenant_id(current_user))


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:

    tenant_id = _tenant_id(current_user)

    revenue_data = await get_revenue_summary(property_id, tenant_id, month, year)

    # round on the Decimal, not on a float
    total_revenue = Decimal(revenue_data['total']).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": float(total_revenue),
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
