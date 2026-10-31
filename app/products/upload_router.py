from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
import os
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business
from app.products.schemas import ProductCreate, ProductRead, ProductUpdate
from app.products import service

router = APIRouter(prefix="/businesses/{business_id}/products", tags=["Products"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product_endpoint(
    business_id: int,
    business: Business = Depends(get_current_business),
    name: str = Form(...),
    sku: str = Form(...),
    description: str | None = Form(None),
    cost_price: float = Form(...),
    selling_price: float = Form(...),
    stock_quantity: int = Form(...),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    """
    Create a product with optional image upload.
    
    Use multipart/form-data with:
    - name: string
    - sku: string
    - cost_price: number
    - selling_price: number
    - stock_quantity: integer
    - description (optional): string
    - file (optional): image file (jpg, png)
    """
    image_url = None
    
    if file:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG and PNG allowed.")
        
        # Save file
        filename = f"{business_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
        
        image_url = f"/uploads/{filename}"
    
    try:
        return service.create_product(
            db=db, 
            business_id=business_id,
            data=ProductCreate(
                name=name,
                sku=sku,
                description=description,
                cost_price=cost_price,
                selling_price=selling_price,
                stock_quantity=stock_quantity,
                image_url=image_url
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
