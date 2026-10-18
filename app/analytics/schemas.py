from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Dict

class DashboardSummary(BaseModel):
    total_revenue: Decimal
    total_profit: Decimal
    total_orders: int
    pending_deliveries: int
    orders_by_status: Dict[str, int]
    
    model_config = ConfigDict(from_attributes=True)
