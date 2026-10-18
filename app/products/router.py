from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business
from app.products.schemas import ProductCreate, ProductRead, ProductUpdate
from app.products import service

router = APIRouter(prefix="/businesses/{business_id}/products", tags=["Products"])

@router.get("/", response_model=list[ProductRead])
def list_products(business_id: int, db: Session = Depends(get_db), current_business: Business = Depends(get_current_business)):
    return service.get_products(db, business_id)

@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product_endpoint(business_id: int, product_data: ProductCreate, db: Session = Depends(get_db), current_business: Business = Depends(get_current_business)):
    try:
        return service.create_product(db, business_id, product_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{product_id}", response_model=ProductRead)
def get_product_endpoint(business_id: int, product_id: int, db: Session = Depends(get_db), current_business: Business = Depends(get_current_business)):
    product = service.get_product(db, business_id, product_id)
    if not product: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=ProductRead)
def update_product_endpoint(business_id: int, product_id: int, product_data: ProductUpdate, db: Session = Depends(get_db), current_business: Business = Depends(get_current_business)):
    product = service.update_product(db, business_id, product_id, product_data)
    if not product: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_endpoint(business_id: int, product_id: int, db: Session = Depends(get_db), current_business: Business = Depends(get_current_business)):
    if not service.delete_product(db, business_id, product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
