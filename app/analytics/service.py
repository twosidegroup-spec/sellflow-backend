from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.base import Order, Delivery
from app.orders.models import OrderStatus
from app.deliveries.models import DeliveryStatus
from app.analytics.schemas import DashboardSummary

def get_dashboard_summary(db: Session, business_id: int) -> DashboardSummary:
    # 1. Calculate Total Revenue and Total Profit from Orders
    # We use COALESCE to return 0 if there are no orders yet
    revenue_result = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
        Order.business_id == business_id
    ).scalar()
    
    profit_result = db.query(func.coalesce(func.sum(Order.gross_profit), 0)).filter(
        Order.business_id == business_id
    ).scalar()
    
    # 2. Calculate Total Orders
    total_orders = db.query(func.count(Order.id)).filter(
        Order.business_id == business_id
    ).scalar()
    
    # 3. Calculate Orders by Status
    status_counts = db.query(Order.status, func.count(Order.id)).filter(
        Order.business_id == business_id
    ).group_by(Order.status).all()
    
    orders_by_status = {status.value: count for status, count in status_counts}
    
    # Ensure all statuses are represented, even if 0
    for status in OrderStatus:
        if status.value not in orders_by_status:
            orders_by_status[status.value] = 0
            
    # 4. Calculate Pending Deliveries (Pending or In Transit)
    pending_deliveries = db.query(func.count(Delivery.id)).filter(
        Delivery.business_id == business_id,
        Delivery.status.in_([DeliveryStatus.PENDING, DeliveryStatus.IN_TRANSIT])
    ).scalar()
    
    return DashboardSummary(
        total_revenue=Decimal(str(revenue_result)),
        total_profit=Decimal(str(profit_result)),
        total_orders=total_orders,
        pending_deliveries=pending_deliveries,
        orders_by_status=orders_by_status
    )
