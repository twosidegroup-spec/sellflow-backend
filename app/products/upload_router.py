from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import os
import re
import secrets
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.core.config import settings
from app.core.storage import UPLOAD_DIR, StorageError, get_storage  # noqa: F401 (UPLOAD_DIR re-exported for tests)
from app.db.base import Business
from app.products.schemas import ProductCreate, ProductRead, ProductUpdate
from app.products import service

router = APIRouter(prefix="/businesses/{business_id}/products", tags=["Products"])
logger = logging.getLogger("sellflow.products.upload")

# UPLOAD_DIR is imported from app.core.storage (re-exported above for tests and
# tooling); the storage backend owns directory creation and write failures.


def _safe_upload_name(original: str | None) -> str:
    """A filesystem-safe stem derived from the client's filename.

    Removes any path components (defence against absolute-path/`..` writes on
    Windows and POSIX) and restricts the character set. The stored extension
    is chosen separately from the validated content type; this function only
    contributes a cosmetic stem.
    """
    base = os.path.basename(original or "upload")
    stem, _ext = os.path.splitext(base)
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem)[:60] or "image"
    return stem


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

        # The stored extension is derived from the (allow-listed) content type,
        # never from the client filename. Otherwise "payload.html" sent with
        # Content-Type: image/png would be stored as .html and served as
        # text/html from the unauthenticated /uploads mount — a stored-XSS
        # vector on the application origin.
        extension_by_type = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
        }
        extension = extension_by_type[(file.content_type or "").lower()]

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # 128 bits of randomness: the file is served from an unauthenticated
        # /uploads mount (capability-URL model), so the name must not be
        # guessable from business id + timestamp + original filename.
        filename = (
            f"{business_id}_{timestamp}_{secrets.token_hex(16)}_"
            f"{_safe_upload_name(file.filename)}{extension}"
        )

        # Persist through the configured backend (local disk or Cloudflare R2).
        # A storage failure must not create a product with a dangling image URL.
        try:
            image_url = get_storage().save(
                filename, content, (file.content_type or "").lower()
            )
        except StorageError as exc:
            logger.warning("product image storage failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Image storage is temporarily unavailable",
            ) from exc
    
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
