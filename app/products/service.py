from sqlalchemy.orm import Session
from app.db.base import Product
from app.products.schemas import ProductCreate, ProductUpdate

def get_products(db: Session, business_id: int) -> list[Product]:
    return db.query(Product).filter(Product.business_id == business_id).all()

def get_product(db: Session, business_id: int, product_id: int) -> Product | None:
    return db.query(Product).filter(Product.id == product_id, Product.business_id == business_id).first()

def create_product(db: Session, business_id: int, product_data: ProductCreate) -> Product:
    existing = db.query(Product).filter(Product.business_id == business_id, Product.sku == product_data.sku).first()
    if existing:
        raise ValueError(f"Product with SKU '{product_data.sku}' already exists")
    
    db_product = Product(
        business_id=business_id, name=product_data.name, sku=product_data.sku,
        description=product_data.description, cost_price=product_data.cost_price,
        selling_price=product_data.selling_price, stock_quantity=product_data.stock_quantity
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, business_id: int, product_id: int, product_data: ProductUpdate) -> Product | None:
    product = get_product(db, business_id, product_id)
    if not product: return None
    for field, value in product_data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product

def delete_product(db: Session, business_id: int, product_id: int) -> bool:
    product = get_product(db, business_id, product_id)
    if not product: return False
    db.delete(product)
    db.commit()
    return True
