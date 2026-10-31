from datetime import datetime
import enum
from sqlalchemy import String, Numeric, Integer, ForeignKey, DateTime, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.engine import Base


class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    status: Mapped[ProductStatus] = mapped_column(Enum(ProductStatus), default=ProductStatus.ACTIVE)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    business = relationship("Business", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

    @property
    def image_url(self) -> str | None:
        """Primary image URL, exposed for API responses (e.g. ProductRead)."""
        return self.images[0].image_url if self.images else None

    @property
    def is_archived(self) -> bool:
        return self.status == ProductStatus.INACTIVE


class ProductImage(Base):
    __tablename__ = "product_images"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    product = relationship("Product", back_populates="images")
