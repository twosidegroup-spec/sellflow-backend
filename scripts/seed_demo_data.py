"""Seed a realistic demo dataset for local UI review.

SAFETY: refuses to run unless the configured database name ends in `_test`
(override with `--allow-non-test`, which you should never need). This script
is for the disposable local test database only; it is not a deployment tool.

Usage (from the backend directory):

    $env:DATABASE_URL = ".../sellflow_migration_test"
    .venv\\Scripts\\python.exe scripts\\seed_demo_data.py

Creates one demo business ("Dhaka Fashion House") with products, customers,
orders across the last 10 days, recorded payments, and payment-intelligence
events processed through the REAL engine (so decisions, matches, anomalies and
review-queue entries are genuine rows, not fixtures).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Make `app.*` importable when this file is executed directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import update

DEMO_EMAIL = "demo@sellflow.app"
DEMO_PASSWORD = "demo1234"
DEMO_BUSINESS = "Dhaka Fashion House"
DEMO_RECEIVING = "01730000000"


def _assert_safe_target() -> None:
    url = os.getenv("DATABASE_URL", "")
    database = url.rsplit("/", 1)[-1].lower() if url else ""
    if not database.endswith("_test") and "--allow-non-test" not in sys.argv:
        print(
            "REFUSING: DATABASE_URL does not name a *_test database. "
            "Nothing was written.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def main() -> int:
    load_dotenv()
    _assert_safe_target()

    from app.auth.service import create_user
    from app.auth.schemas import UserCreate
    from app.core.security import get_password_hash
    from app.customers.schemas import CustomerCreate
    from app.customers import service as customer_service
    from app.db.base import (
        Business,
        Customer,
        Delivery,
        DetectedPayment,
        Device,
        DevicePairingCode,
        Membership,
        Order,
        OrderItem,
        Payment,
        PaymentAccount,
        Product,
        ProductImage,
        User,
        WebhookSubscription,
    )
    from app.db.engine import SessionLocal
    from app.orders.models import OrderStatus
    from app.orders.schemas import OrderCreate, OrderItemCreate
    from app.orders import service as order_service
    from app.payments.intelligence.db_models import (
        PaymentAnomaly,
        PaymentDecision,
        PaymentEvent,
        PaymentFeedback,
        PaymentMatch,
    )
    from app.payments.intelligence.models import PaymentEventCreate, PaymentSourceType
    from app.payments.intelligence.service import PAYMENT_INTELLIGENCE_SERVICE
    from app.payments.models import PaymentStatus
    from app.products.schemas import ProductCreate
    from app.products import service as product_service

    now = datetime.now(timezone.utc)
    db = SessionLocal()

    print("Wiping business data (disposable test database)…")
    db.query(PaymentFeedback).delete()
    db.query(PaymentAnomaly).delete()
    db.query(PaymentMatch).delete()
    db.query(PaymentDecision).delete()
    db.query(PaymentEvent).delete()
    db.query(DetectedPayment).delete()
    db.query(Payment).delete()
    db.query(OrderItem).delete()
    db.query(Delivery).delete()
    db.query(Order).delete()
    db.query(ProductImage).delete()
    db.query(Product).delete()
    db.query(Customer).delete()
    db.query(Device).delete()
    db.query(DevicePairingCode).delete()
    db.query(Membership).delete()
    db.query(WebhookSubscription).delete()
    db.query(User).delete()
    db.query(Business).delete()
    db.commit()

    # ---------------------------------------------------------------- account
    user, business = create_user(
        db,
        UserCreate(
            email=DEMO_EMAIL,
            full_name="Rahim Uddin",
            password=DEMO_PASSWORD,
            phone=DEMO_RECEIVING,
            business_name=DEMO_BUSINESS,
        ),
    )
    user.hashed_password = get_password_hash(DEMO_PASSWORD)
    db.commit()
    business_id = business.id
    print(f"Business #{business_id} '{business.name}' / user {user.email}")

    db.add(
        PaymentAccount(
            business_id=business_id,
            provider="bkash",
            receiving_number="8801730000000",
            status="configured",
            mode="live",
        )
    )
    db.commit()

    # ---------------------------------------------------------------- products
    product_rows = [
        ("Cotton Panjabi — Navy", "PAN-NAVY-01", "1850.00", "1150.00", 24),
        ("Karchupi Saree — Teal", "SAR-TEAL-02", "4200.00", "2600.00", 8),
        ("Silk Scarf — Ivory", "SCF-IVORY-03", "650.00", "280.00", 40),
        ("Denim Jacket — Indigo", "JKT-IND-04", "2450.00", "1500.00", 12),
        ("Kurti — Rosewood", "KRT-ROSE-05", "1250.00", "700.00", 30),
        ("Leather Handbag — Tan", "BAG-TAN-06", "3100.00", "1900.00", 6),
        ("Sneakers — Cloud White", "SNK-WHT-07", "2850.00", "1750.00", 14),
        ("Panjabi Set — Festive", "PAN-SET-08", "3400.00", "2100.00", 3),
    ]
    products = []
    for name, sku, price, cost, stock in product_rows:
        products.append(
            product_service.create_product(
                db,
                business_id,
                ProductCreate(
                    name=name,
                    sku=sku,
                    cost_price=Decimal(cost),
                    selling_price=Decimal(price),
                    stock_quantity=stock,
                ),
            )
        )
    print(f"{len(products)} products")

    # --------------------------------------------------------------- customers
    customer_rows = [
        ("Nusrat Jahan", "01711000001", "nusrat@example.com", "Dhanmondi, Dhaka"),
        ("Tanvir Ahmed", "01811000002", "tanvir@example.com", "Mirpur, Dhaka"),
        ("Farhana Islam", "01911000003", "farhana@example.com", "Gulshan, Dhaka"),
        ("Imran Hossain", "01611000004", "imran@example.com", "Uttara, Dhaka"),
        ("Sadia Rahman", "01511000005", "sadia@example.com", "Banani, Dhaka"),
        ("Mahmudul Hasan", "01311000006", "mahmud@example.com", "Mohammadpur, Dhaka"),
    ]
    customers = []
    for name, phone, email, address in customer_rows:
        customers.append(
            customer_service.create_customer(
                db,
                business_id,
                CustomerCreate(name=name, phone=phone, email=email, address=address),
            )
        )
    print(f"{len(customers)} customers")

    # ------------------------------------------------------------------ orders
    def make_order(
        customer,
        product,
        quantity,
        status,
        days_ago,
        delivery_fee="80.00",
        discount="0.00",
    ):
        order = order_service.create_order(
            db,
            business_id,
            OrderCreate(
                customer_id=customer.id,
                items=[
                    OrderItemCreate(
                        product_id=product.id,
                        product_name=product.name,
                        quantity=quantity,
                        unit_price=Decimal(str(product.selling_price)),
                        unit_cost=Decimal(str(product.cost_price)),
                    )
                ],
                delivery_fee=Decimal(delivery_fee),
                discount=Decimal(discount),
            ),
        )
        when = now - timedelta(days=days_ago, hours=2)
        db.execute(
            update(Order).where(Order.id == order.id).values(created_at=when, updated_at=when)
        )
        order.status = status
        db.commit()
        db.refresh(order)
        return order

    statuses = [
        (OrderStatus.DELIVERED, 9),
        (OrderStatus.DELIVERED, 8),
        (OrderStatus.SHIPPED, 7),
        (OrderStatus.DELIVERED, 6),
        (OrderStatus.CONFIRMED, 5),
        (OrderStatus.SHIPPED, 4),
        (OrderStatus.DELIVERED, 3),
        (OrderStatus.CREATED, 3),
        (OrderStatus.CONFIRMED, 2),
        (OrderStatus.SHIPPED, 2),
        (OrderStatus.CREATED, 1),
        (OrderStatus.CONFIRMED, 1),
        (OrderStatus.CANCELLED, 1),
        (OrderStatus.CREATED, 0),
        (OrderStatus.CONFIRMED, 0),
        (OrderStatus.CREATED, 0),
    ]
    orders = []
    for index, (status, days_ago) in enumerate(statuses):
        product = products[index % len(products)]
        customer = customers[index % len(customers)]
        quantity = 1 if index % 4 else 2
        orders.append(make_order(customer, product, quantity, status, days_ago))

    # Two dedicated customers with exactly ONE order each, so the seeded
    # partial-payment and overpayment scenarios match unambiguously.
    partial_demo_customer = customer_service.create_customer(
        db,
        business_id,
        CustomerCreate(name="Shamim Reza", phone="01911000012", address="Bashundhara, Dhaka"),
    )
    partial_demo_order = make_order(
        partial_demo_customer, products[1], 1, OrderStatus.CONFIRMED, 1
    )
    over_demo_customer = customer_service.create_customer(
        db,
        business_id,
        CustomerCreate(name="Ayesha Siddiqua", phone="01811000011", address="Chattogram"),
    )
    over_demo_order = make_order(
        over_demo_customer, products[0], 2, OrderStatus.CREATED, 1
    )
    customers.extend([partial_demo_customer, over_demo_customer])
    orders.extend([partial_demo_order, over_demo_order])
    print(f"{len(orders)} orders (incl. 2 scenario orders)")

    # -------------------------------------------------- recorded payments rows
    paid_orders = [o for o in orders if o.status == OrderStatus.DELIVERED][:3]
    for order in paid_orders:
        db.add(
            Payment(
                business_id=business_id,
                order_id=order.id,
                amount=order.total_amount,
                method="bkash",
                transaction_id=f"SEEDPAY{order.id:04d}",
                status=PaymentStatus.VERIFIED,
                notes="Seeded recorded payment",
                paid_at=order.created_at + timedelta(hours=3),
            )
        )
        order.payment_status = "paid"
        order.payment_method = "bkash"
    db.commit()
    print(f"{len(paid_orders)} recorded payments")

    # ------------------------------------------- payment intelligence events
    # Real engine runs: decisions, matches, anomalies and review queue are the
    # genuine outputs of the migrated pipeline.
    def event(txn, amount, sender, days_ago, source="android_sms"):
        PAYMENT_INTELLIGENCE_SERVICE.ingest_event(
            db,
            business_id=business_id,
            payload=PaymentEventCreate(
                transaction_id=txn,
                amount=Decimal(amount),
                currency="BDT",
                sender_identifier=sender,
                receiver_identifier=DEMO_RECEIVING,
                timestamp=(now - timedelta(days=days_ago, hours=1)).isoformat(),
                source_type=(
                    PaymentSourceType.SMS if source == "android_sms" else PaymentSourceType.DEVICE_EVENT
                ),
                source=source,
            ),
            provider="bkash",
        )

    unpaid = [o for o in orders if o.status != OrderStatus.CANCELLED and o.payment_status != "paid"]
    customers_by_id = {c.id: c for c in customers}
    orders_by_customer = {}
    for order_ in orders:
        orders_by_customer.setdefault(order_.customer_id, []).append(order_)

    def phone_of(order):
        customer = customers_by_id.get(order.customer_id)
        return customer.phone if customer else None

    def single_order_customers(pool):
        """Orders whose customer has exactly one order — keeps matching unambiguous."""
        return [o for o in pool if len(orders_by_customer.get(o.customer_id, [])) == 1]

    # Exact-amount matches (candidate found by the order's own customer phone
    # for the first two -> AUTO_MATCHED; without phone -> PAID with the
    # lower-confidence decision recorded).
    event("BX71A2QK9D", str(unpaid[0].total_amount), phone_of(unpaid[0]), 2)
    event("BX72B3RL8E", str(unpaid[1].total_amount), phone_of(unpaid[1]), 2)
    event("BX73C4SM7F", str(unpaid[2].total_amount), None, 1)
    event("BX74D5TN6G", str(unpaid[3].total_amount), None, 1)

    # Partial settlement: a deterministic single-order customer, its phone,
    # and an amount strictly below the order total.
    partial_pool = [o for o in single_order_customers(unpaid) if Decimal(str(o.total_amount)) > Decimal("3000")]
    partial_order = (partial_pool or single_order_customers(unpaid))[0]
    partial_amount = (Decimal(str(partial_order.total_amount)) * Decimal("0.4")).quantize(Decimal("0.01"))
    event("BX75E6UP5H", str(partial_amount), phone_of(partial_order), 1)

    # Overpayment: another deterministic single-order customer, 3x its total.
    over_pool = [o for o in single_order_customers(unpaid) if o.id != partial_order.id]
    over_order = (over_pool or [o for o in unpaid if o.id != partial_order.id])[0]
    over_amount = (Decimal(str(over_order.total_amount)) * Decimal("3")).quantize(Decimal("0.01"))
    event("BX76F7VQ4J", str(over_amount), phone_of(over_order), 1)

    # Unmatched payments -> review queue.
    event("BX77G8WR3K", "3650.00", "01799000111", 1)
    event("BX78H9XS2L", "712.50", None, 0)
    # Duplicate replay of an existing transaction.
    event("BX71A2QK9D", "10.00", None, 0)
    db.commit()
    print("payment-intelligence events ingested (real engine)")

    summary = PAYMENT_INTELLIGENCE_SERVICE.summary(db, business_id)
    print("Summary:", {k: summary[k] for k in ("total_events", "paid_events", "review_events", "duplicate_events")})

    db.close()
    print()
    print("Demo login: " + DEMO_EMAIL + " / " + DEMO_PASSWORD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
