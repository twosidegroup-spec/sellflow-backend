from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.base import Order, OrderItem, Product, Customer
from app.orders.models import OrderStatus, Order as _OrderModel  # noqa: F401
from app.orders.schemas import OrderCreate
from app.products.models import ProductStatus


def create_order(db: Session, business_id: int, order_data: OrderCreate) -> Order:
    # 1. Initialize totals
    total_amount = Decimal("0.00")
    total_cost = Decimal("0.00")
    
    # 2. Create the Order shell first to get an ID
    db_order = Order(
        business_id=business_id,
        customer_id=order_data.customer_id,
        delivery_fee=order_data.delivery_fee,
        discount=order_data.discount,
        notes=order_data.notes,
        is_cod=bool(order_data.is_cod),
        total_amount=0.0, # Will be updated
        total_cost=0.0,   # Will be updated
        gross_profit=0.0  # Will be updated
    )
    db.add(db_order)
    db.flush() # Gets the order.id without committing
    
    # 3. Process each item and calculate line totals
    for item_data in order_data.items:
        # Optional: Verify product belongs to this business if product_id is provided
        if item_data.product_id:
            product = db.query(Product).filter(
                Product.id == item_data.product_id,
                Product.business_id == business_id
            ).first()
            if not product:
                raise ValueError(f"Product {item_data.product_id} not found in this business")
            if product.status != ProductStatus.ACTIVE:
                raise ValueError(
                    f"Product {item_data.product_id} is archived and cannot be ordered"
                )
            
            # Use product's current cost if not explicitly provided, otherwise use provided
            unit_cost = item_data.unit_cost if item_data.unit_cost is not None else product.cost_price
        else:
            unit_cost = item_data.unit_cost or Decimal("0.00")
            
        quantity = Decimal(str(item_data.quantity))
        unit_price = item_data.unit_price
        
        line_total = unit_price * quantity
        cost_total = unit_cost * quantity
        profit = line_total - cost_total # Can be negative!
        
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=item_data.product_id,
            product_name=item_data.product_name,
            quantity=item_data.quantity,
            unit_price=float(unit_price),
            unit_cost=float(unit_cost),
            line_total=float(line_total),
            cost_total=float(cost_total),
            profit=float(profit)
        )
        db.add(db_item)
        
        total_amount += line_total
        total_cost += cost_total
        
    # 4. Calculate final order totals
    gross_profit = (total_amount - total_cost) - order_data.discount
    final_amount = total_amount + order_data.delivery_fee - order_data.discount

    # A discount may never push the amount due below zero. The previous
    # behaviour accepted arbitrarily large discounts and stored negative
    # totals (reducing reported revenue and corrupting profit figures).
    if final_amount < 0:
        raise ValueError(
            "Discount cannot exceed the item subtotal plus the delivery fee"
        )

    db_order.total_amount = float(final_amount)
    db_order.total_cost = float(total_cost)
    db_order.gross_profit = float(gross_profit)
    
    db.commit()
    db.refresh(db_order)
    return db_order

def get_orders(
    db: Session,
    business_id: int,
    *,
    q: str | None = None,
    status: OrderStatus | None = None,
    sort: str = "newest",
    limit: int | None = None,
    offset: int = 0,
) -> list[Order]:
    """List orders for one business with optional search/filter/sort/page.

    Defaults (no arguments) keep the original behaviour: every order, newest
    first — so existing clients and tests are unaffected.
    """
    query = db.query(Order).filter(Order.business_id == business_id)

    if status is not None:
        query = query.filter(Order.status == status)

    if q and q.strip():
        term = q.strip()
        conditions = [Order.customer.has(Customer.name.ilike(f"%{term}%"))]
        if term.isdigit():
            conditions.append(Order.id == int(term))
        query = query.filter(or_(*conditions))

    if sort == "oldest":
        query = query.order_by(Order.created_at.asc(), Order.id.asc())
    elif sort == "amount_desc":
        query = query.order_by(Order.total_amount.desc(), Order.id.desc())
    elif sort == "amount_asc":
        query = query.order_by(Order.total_amount.asc(), Order.id.asc())
    else:
        query = query.order_by(Order.created_at.desc(), Order.id.desc())

    if offset:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    return query.all()

def get_order(db: Session, business_id: int, order_id: int) -> Order | None:
    return db.query(Order).filter(Order.id == order_id, Order.business_id == business_id).first()
