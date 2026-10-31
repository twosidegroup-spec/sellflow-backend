from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
import os
import re
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.core.config import settings
from app.db.base import Business
from app.products.schemas import ProductCreate, ProductRead, ProductUpdate
from app.products import service

router = APIRouter(prefix="/businesses/{business_id}/products", tags=["Products"])

# Canonical upload directory: <backend>/uploads (contains .gitkeep, gitignored).
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _safe_upload_name(original: str | None) -> str:
    """A filesystem-safe, collision-resistant name derived from the client's.

    Removes any path components (defence against absolute-path/`..` writes on
    Windows and POSIX) and restricts the character set. The stored filename is
    always generated server-side; the original name is never trusted.
    """
    base = os.path.basename(original or "upload")
    stem, ext = os.path.splitext(base)
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem)[:60] or "image"
    ext = re.sub(r"[^A-Za-z0-9.]", "", ext.lower())[:10]
    return f"{stem}{ext}"


@router.post("/upload", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
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
    Create a product with optional image upload (multipart/form-data).

    NOTE (migration): the JSON `POST /products/` route in `products/router.py`
    is the CANONICAL create endpoint used by the Flutter app. This multipart
    variant is retained for future use and is reachable via the distinct path
    `/products/upload` (see `main.py`), which removes the previous duplicate
    route/method conflict that made this handler unreachable.
    """
    image_url = None
    
    if file:
        allowed_types = settings.allowed_upload_type_list
        if file.content_type and file.content_type.lower() not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}",
            )

        content = file.file.read(settings.max_upload_size + 1)
        if len(content) > settings.max_upload_size:
            raise HTTPException(status_code=400, detail="File is too large")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{business_id}_{timestamp}_{_safe_upload_name(file.filename)}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            buffer.write(content)
        
        image_url = f"/uploads/{filename}"
    
    try:
        product = service.create_product(
            db=db,
            business_id=business_id,
            product_data=ProductCreate(
                name=name,
                sku=sku,
                description=description,
                cost_price=cost_price,
                selling_price=selling_price,
                stock_quantity=stock_quantity,
                image_url=image_url,
            ),
        )
        if image_url:
            from app.products.models import ProductImage

            product.images.append(ProductImage(image_url=image_url))
            db.commit()
            db.refresh(product)
        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
