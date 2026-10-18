from decimal import Decimal
from sqlalchemy.orm import Session
from app.db.base import Order, OrderItem, Product
from app.orders.schemas import OrderCreate

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
    
    db_order.total_amount = float(final_amount)
    db_order.total_cost = float(total_cost)
    db_order.gross_profit = float(gross_profit)
    
    db.commit()
    db.refresh(db_order)
    return db_order

def get_orders(db: Session, business_id: int) -> list[Order]:
    return db.query(Order).filter(Order.business_id == business_id).order_by(Order.created_at.desc()).all()

def get_order(db: Session, business_id: int, order_id: int) -> Order | None:
    return db.query(Order).filter(Order.id == order_id, Order.business_id == business_id).first()
