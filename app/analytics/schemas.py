from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Dict, List

class DailyPoint(BaseModel):
    date: str          # YYYY-MM-DD (server-local day)
    revenue: Decimal
    profit: Decimal
    orders: int

class DashboardSummary(BaseModel):
    total_revenue: Decimal
    total_profit: Decimal
    total_orders: int
    pending_deliveries: int
    orders_by_status: Dict[str, int]
    # Today (server-local day)
    today_revenue: Decimal = Decimal("0")
    today_profit: Decimal = Decimal("0")
    today_orders: int = 0
    # Last 7 local days, oldest first
    daily: List[DailyPoint] = []

    model_config = ConfigDict(from_attributes=True)
