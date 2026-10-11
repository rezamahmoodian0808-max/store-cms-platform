from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ColorVariant(BaseModel):
    id: str = Field(default="1")
    name: str
    hex: str = Field(default="#000000")
    image: Optional[str] = ""
    price: Optional[float] = None
    sku: Optional[str] = ""
    stock: int = 10

class ProductCreate(BaseModel):
    title: str
    slug: str
    sku: Optional[str] = ""
    category_id: Optional[int] = None
    price: float
    compare_at_price: Optional[float] = None
    stock_quantity: int = 10
    is_in_stock: bool = True
    featured_image: Optional[str] = ""
    gallery_images: List[str] = []
    short_description: Optional[str] = ""
    description: Optional[str] = ""
    is_featured: bool = False
    is_published: bool = True

    # Feature A: Priority / Ordering
    has_priority_system: bool = False
    priority_label_1: str = "انتخاب اولویت اول / Priority 1"
    priority_label_2: str = "انتخاب اولویت دوم / Priority 2"
    priority_options: List[str] = []
    priority_helper_text: str = "در صورت موجود نبودن اولویت اول، اولویت دوم برای شما ارسال می‌گردد."

    # Feature B: Color variants
    has_color_variants: bool = False
    color_variants: List[ColorVariant] = []

    meta_title: Optional[str] = ""
    meta_description: Optional[str] = ""

class PageCreate(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = ""
    body_content: str
    template_type: str = "standard"
    is_published: bool = True
    sort_order: int = 0
    meta_title: Optional[str] = ""
    meta_description: Optional[str] = ""

class BlogPostCreate(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = ""
    content: str
    featured_image: Optional[str] = ""
    category: str = "اخبار و مقالات / Articles"
    tags: Optional[str] = ""
    author_name: str = "مدیریت / Admin"
    is_published: bool = True
    meta_title: Optional[str] = ""
    meta_description: Optional[str] = ""

class InquiryCreate(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = ""
    subject: Optional[str] = ""
    message: str
