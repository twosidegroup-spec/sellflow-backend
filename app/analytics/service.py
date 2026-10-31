from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.base import Order, Delivery
from app.orders.models import OrderStatus
from app.deliveries.models import DeliveryStatus
from app.analytics.schemas import DashboardSummary, DailyPoint

def get_dashboard_summary(db: Session, business_id: int) -> DashboardSummary:
    # 1. Calculate Total Revenue and Total Profit from Orders.
    # Cancelled orders are excluded: counting them as revenue overstates the
    # seller's takings. (Previously included; corrected during the migration.)
    revenue_result = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
        Order.business_id == business_id,
        Order.status != OrderStatus.CANCELLED,
    ).scalar()
    
    profit_result = db.query(func.coalesce(func.sum(Order.gross_profit), 0)).filter(
        Order.business_id == business_id,
        Order.status != OrderStatus.CANCELLED,
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

    # 5. Today's numbers + last 7 local days (oldest first)
    local_now = datetime.now().astimezone()
    local_tz = local_now.tzinfo
    local_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = local_today - timedelta(days=6)

    recent_orders = db.query(
        Order.created_at, Order.total_amount, Order.gross_profit
    ).filter(
        Order.business_id == business_id,
        Order.created_at >= week_start.astimezone(timezone.utc),
    ).all()

    daily: list[DailyPoint] = []
    for i in range(7):
        day_start = week_start + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_revenue = Decimal("0")
        day_profit = Decimal("0")
        day_orders = 0
        for created_at, total, profit in recent_orders:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            local_dt = created_at.astimezone(local_tz)
            if day_start <= local_dt < day_end:
                day_revenue += Decimal(str(total or 0))
                day_profit += Decimal(str(profit or 0))
                day_orders += 1
        daily.append(DailyPoint(
            date=day_start.strftime("%Y-%m-%d"),
            revenue=day_revenue,
            profit=day_profit,
            orders=day_orders,
        ))

    today = daily[-1]

    return DashboardSummary(
        total_revenue=Decimal(str(revenue_result)),
        total_profit=Decimal(str(profit_result)),
        total_orders=total_orders,
        pending_deliveries=pending_deliveries,
        orders_by_status=orders_by_status,
        today_revenue=today.revenue,
        today_profit=today.profit,
        today_orders=today.orders,
        daily=daily,
    )
