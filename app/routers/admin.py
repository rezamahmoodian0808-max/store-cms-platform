import json
import os
import shutil
import time
from typing import Optional
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.database import get_db, set_setting, get_all_settings
from app.auth import (
    verify_password,
    create_session_token,
    require_auth,
    SESSION_COOKIE_NAME
)
from app.helpers import get_site_context, parse_json_field, invalidate_navigation_cache

from app.config import settings

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)

# ==================== AUTHENTICATION ====================

@router.get("/login")
def login_page(request: Request, error: Optional[str] = None):
    """Admin login page."""
    ctx = get_site_context(request, {
        "title": "ورود به بخش مدیریت / Admin Login",
        "error": error
    })
    return templates.TemplateResponse(request=request, name="admin/login.html", context=ctx)

@router.post("/login")
def process_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """Processes login credentials and sets signed cookie."""
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()

    if not user or not verify_password(password, user["password_hash"], user["salt"]):
        return RedirectResponse(url="/admin/login?error=invalid_credentials", status_code=303)

    if not user["is_active"]:
        return RedirectResponse(url="/admin/login?error=account_disabled", status_code=303)

    token = create_session_token({
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"]
    })

    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=7 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.FORCE_HTTPS
    )
    return response

@router.get("/logout")
def logout():
    """Logs out admin user."""
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response

# ==================== DASHBOARD ====================

@router.get("")
@router.get("/")
def dashboard(request: Request):
    """Admin dashboard overview."""
    user = require_auth(request)

    with get_db() as conn:
        products_count = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
        pages_count = conn.execute("SELECT COUNT(*) as c FROM pages").fetchone()["c"]
        posts_count = conn.execute("SELECT COUNT(*) as c FROM blog_posts").fetchone()["c"]
        inquiries_count = conn.execute("SELECT COUNT(*) as c FROM inquiries").fetchone()["c"]
        unread_inquiries = conn.execute("SELECT COUNT(*) as c FROM inquiries WHERE is_read = 0").fetchone()["c"]

        recent_inquiries = conn.execute(
            "SELECT * FROM inquiries ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        recent_products = conn.execute(
            "SELECT * FROM products ORDER BY id DESC LIMIT 5"
        ).fetchall()

    ctx = get_site_context(request, {
        "title": "داشبورد مدیریت / Admin Dashboard",
        "current_user": user,
        "stats": {
            "products": products_count,
            "pages": pages_count,
            "posts": posts_count,
            "inquiries": inquiries_count,
            "unread_inquiries": unread_inquiries,
        },
        "recent_inquiries": [dict(r) for r in recent_inquiries],
        "recent_products": [dict(r) for r in recent_products],
    })
    return templates.TemplateResponse(request=request, name="admin/dashboard.html", context=ctx)

# ==================== PRODUCTS ====================

@router.get("/products")
def products_list(request: Request):
    """Lists all products in admin."""
    user = require_auth(request)
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY p.id DESC
            """
        ).fetchall()

    products = []
    for r in rows:
        item = dict(r)
        item["color_variants"] = parse_json_field(item.get("color_variants"))
        item["priority_options"] = parse_json_field(item.get("priority_options"))
        products.append(item)

    ctx = get_site_context(request, {
        "title": "مدیریت محصولات / Products Management",
        "current_user": user,
        "products": products,
    })
    return templates.TemplateResponse(request=request, name="admin/products_list.html", context=ctx)

@router.get("/products/new")
def product_new(request: Request):
    """New product editor form."""
    user = require_auth(request)
    with get_db() as conn:
        categories = conn.execute("SELECT * FROM categories ORDER BY name ASC").fetchall()

    ctx = get_site_context(request, {
        "title": "افزودن محصول جدید / Add New Product",
        "current_user": user,
        "product": None,
        "all_categories": [dict(c) for c in categories],
    })
    return templates.TemplateResponse(request=request, name="admin/product_edit.html", context=ctx)

@router.get("/products/{product_id}/edit")
def product_edit(request: Request, product_id: int):
    """Edit product form."""
    user = require_auth(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        categories = conn.execute("SELECT * FROM categories ORDER BY name ASC").fetchall()

    product = dict(row)
    product["color_variants"] = parse_json_field(product.get("color_variants"))
    product["priority_options"] = parse_json_field(product.get("priority_options"))
    product["gallery_images"] = parse_json_field(product.get("gallery_images"))

    ctx = get_site_context(request, {
        "title": f"ویرایش محصول: {product['title']} / Edit Product",
        "current_user": user,
        "product": product,
        "all_categories": [dict(c) for c in categories],
    })
    return templates.TemplateResponse(request=request, name="admin/product_edit.html", context=ctx)

@router.post("/products/save")
def product_save(
    request: Request,
    product_id: Optional[int] = Form(None),
    title: str = Form(...),
    slug: str = Form(...),
    sku: str = Form(""),
    category_id: Optional[int] = Form(None),
    price: float = Form(0.0),
    compare_at_price: Optional[str] = Form(None),
    stock_quantity: int = Form(10),
    is_in_stock: Optional[str] = Form(None),
    featured_image: str = Form(""),
    gallery_images: str = Form("[]"),
    short_description: str = Form(""),
    description: str = Form(""),
    is_featured: Optional[str] = Form(None),
    is_published: Optional[str] = Form(None),

    # Feature A: Priority
    has_priority_system: Optional[str] = Form(None),
    priority_label_1: str = Form("انتخاب اولویت اول / Priority 1"),
    priority_label_2: str = Form("انتخاب اولویت دوم / Priority 2"),
    priority_options_raw: str = Form(""), # newline or comma separated
    priority_helper_text: str = Form(""),

    # Feature B: Color variants
    has_color_variants: Optional[str] = Form(None),
    color_variants_json: str = Form("[]"),

    meta_title: str = Form(""),
    meta_description: str = Form("")
):
    """Saves new or existing product with modular priority & color systems."""
    require_auth(request)

    # Process booleans
    in_stock_val = 1 if is_in_stock else 0
    featured_val = 1 if is_featured else 0
    published_val = 1 if is_published else 0
    priority_val = 1 if has_priority_system else 0
    color_val = 1 if has_color_variants else 0

    # Parse compare price
    comp_price = float(compare_at_price) if compare_at_price and compare_at_price.strip() else None

    # Parse priority options
    options_list = [opt.strip() for opt in priority_options_raw.replace("\r", "").split("\n") if opt.strip()]
    if not options_list and "," in priority_options_raw:
        options_list = [opt.strip() for opt in priority_options_raw.split(",") if opt.strip()]
    priority_options_json = json.dumps(options_list, ensure_ascii=False)

    # Validate color variants JSON
    try:
        parsed_colors = json.loads(color_variants_json)
        color_variants_clean = json.dumps(parsed_colors, ensure_ascii=False)
    except Exception:
        color_variants_clean = "[]"

    # Gallery images JSON
    try:
        parsed_gallery = json.loads(gallery_images)
        gallery_clean = json.dumps(parsed_gallery, ensure_ascii=False)
    except Exception:
        gallery_clean = "[]"

    clean_slug = slug.strip().lower()
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM products WHERE slug = ?", (clean_slug,)).fetchone()
        if existing and (not product_id or existing["id"] != product_id):
            clean_slug = f"{clean_slug}-{int(time.time())}"

        if product_id:
            conn.execute(
                """
                UPDATE products SET
                    title = ?, slug = ?, sku = ?, category_id = ?, price = ?, compare_at_price = ?,
                    stock_quantity = ?, is_in_stock = ?, featured_image = ?, gallery_images = ?,
                    short_description = ?, description = ?, is_featured = ?, is_published = ?,
                    has_priority_system = ?, priority_label_1 = ?, priority_label_2 = ?,
                    priority_options = ?, priority_helper_text = ?,
                    has_color_variants = ?, color_variants = ?,
                    meta_title = ?, meta_description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    title.strip(), clean_slug, sku.strip(), category_id or None, price, comp_price,
                    stock_quantity, in_stock_val, featured_image.strip(), gallery_clean,
                    short_description.strip(), description.strip(), featured_val, published_val,
                    priority_val, priority_label_1.strip(), priority_label_2.strip(),
                    priority_options_json, priority_helper_text.strip(),
                    color_val, color_variants_clean,
                    meta_title.strip(), meta_description.strip(),
                    product_id
                )
            )
        else:
            conn.execute(
                """
                INSERT INTO products (
                    title, slug, sku, category_id, price, compare_at_price,
                    stock_quantity, is_in_stock, featured_image, gallery_images,
                    short_description, description, is_featured, is_published,
                    has_priority_system, priority_label_1, priority_label_2,
                    priority_options, priority_helper_text,
                    has_color_variants, color_variants,
                    meta_title, meta_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(), clean_slug, sku.strip(), category_id or None, price, comp_price,
                    stock_quantity, in_stock_val, featured_image.strip(), gallery_clean,
                    short_description.strip(), description.strip(), featured_val, published_val,
                    priority_val, priority_label_1.strip(), priority_label_2.strip(),
                    priority_options_json, priority_helper_text.strip(),
                    color_val, color_variants_clean,
                    meta_title.strip(), meta_description.strip()
                )
            )

    return RedirectResponse(url="/admin/products", status_code=303)

@router.post("/products/{product_id}/delete")
def product_delete(request: Request, product_id: int):
    """Deletes a product."""
    require_auth(request)
    with get_db() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    return RedirectResponse(url="/admin/products", status_code=303)

# ==================== CMS DYNAMIC PAGES (100+ PAGES) ====================

@router.get("/pages")
def pages_list(request: Request):
    """Lists CMS pages with count and search."""
    user = require_auth(request)
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM pages ORDER BY sort_order ASC, id DESC").fetchall()

    ctx = get_site_context(request, {
        "title": "مدیریت برگه\u200cها / Dynamic Pages Management",
        "current_user": user,
        "pages": [dict(r) for r in rows],
        "total_pages": len(rows),
    })
    return templates.TemplateResponse(request=request, name="admin/pages_list.html", context=ctx)

@router.get("/pages/new")
def page_new(request: Request):
    """Creates a new CMS page."""
    user = require_auth(request)
    ctx = get_site_context(request, {
        "title": "افزودن برگه جدید / Add New Page",
        "current_user": user,
        "page": None,
    })
    return templates.TemplateResponse(request=request, name="admin/page_edit.html", context=ctx)

@router.get("/pages/{page_id}/edit")
def page_edit(request: Request, page_id: int):
    """Edits an existing CMS page."""
    user = require_auth(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Page not found")

    ctx = get_site_context(request, {
        "title": f"ویرایش برگه: {row['title']} / Edit Page",
        "current_user": user,
        "page": dict(row),
    })
    return templates.TemplateResponse(request=request, name="admin/page_edit.html", context=ctx)

@router.post("/pages/save")
def page_save(
    request: Request,
    page_id: Optional[int] = Form(None),
    title: str = Form(...),
    slug: str = Form(...),
    excerpt: str = Form(""),
    body_content: str = Form(...),
    template_type: str = Form("standard"),
    is_published: Optional[str] = Form(None),
    sort_order: int = Form(0),
    meta_title: str = Form(""),
    meta_description: str = Form("")
):
    """Saves CMS page."""
    require_auth(request)
    published_val = 1 if is_published else 0

    clean_slug = slug.strip().lower()
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM pages WHERE slug = ?", (clean_slug,)).fetchone()
        if existing and (not page_id or existing["id"] != page_id):
            clean_slug = f"{clean_slug}-{int(time.time())}"

        if page_id:
            conn.execute(
                """
                UPDATE pages SET
                    title = ?, slug = ?, excerpt = ?, body_content = ?, template_type = ?,
                    is_published = ?, sort_order = ?, meta_title = ?, meta_description = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    title.strip(), clean_slug, excerpt.strip(), body_content.strip(),
                    template_type, published_val, sort_order, meta_title.strip(), meta_description.strip(),
                    page_id
                )
            )
        else:
            conn.execute(
                """
                INSERT INTO pages (
                    title, slug, excerpt, body_content, template_type,
                    is_published, sort_order, meta_title, meta_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(), clean_slug, excerpt.strip(), body_content.strip(),
                    template_type, published_val, sort_order, meta_title.strip(), meta_description.strip()
                )
            )

    return RedirectResponse(url="/admin/pages", status_code=303)

@router.post("/pages/{page_id}/delete")
def page_delete(request: Request, page_id: int):
    """Deletes a CMS page."""
    require_auth(request)
    with get_db() as conn:
        conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))
    return RedirectResponse(url="/admin/pages", status_code=303)

@router.post("/pages/bulk-generate")
def page_bulk_generate(request: Request, count: int = Form(25)):
    """
    Auto-generates structured CMS pages (demonstrates instant scaling to 100+ pages!).
    Creates city service pages, stationery guide pages, and corporate landing pages.
    """
    require_auth(request)
    topics = [
        ("خرید عمده نوشت افزار در {}", "bulk-stationery-{}", "راهنمای تخصصی و شرایط ثبت سفارش عمده نوشت افزار و لوازم تحریر برای مدارس، ادارات و سازمان‌ها در {}."),
        ("تامین لوازم التحریر اداری در {}", "office-stationery-{}", "پکیج‌های اقتصادی و اداری نوشت‌افزار ویژه شرکت‌ها، بانک‌ها و موسسات در {} با فاکتور رسمی."),
        ("نمایندگی پخش نوشت‌افزار در {}", "stationery-agency-{}", "مرکز پخش مستقیم محصولات تحریری برندهای پنتر، پرشیا، کنکو و فابر کاستل در {} با ارسال سریع."),
        ("راهنمای انتخاب خودکار و روان‌نویس برای {}", "pen-guide-{}", "بررسی بهترین برندهای قلم، ماژیک وایت‌برد و خودکارهای ارگونومیک برای مهندسین و اساتید در {}."),
    ]
    cities = [
        "تهران", "شیراز", "اصفهان", "مشهد", "تبریز", "کرج", "اهواز", "قم", "کرمانشاه", "ارومیه",
        "رشت", "زاهدان", "همدان", "یزد", "اردبیل", "بندرعباس", "اراک", "زنجان", "سنندج", "قزوین",
        "خرم‌آباد", "گرگان", "ساری", "بوشهر", "کرمان"
    ]

    created = 0
    with get_db() as conn:
        for idx in range(min(count, 100)):
            topic = topics[idx % len(topics)]
            city = cities[idx % len(cities)]
            title = topic[0].format(city)
            slug = topic[1].format(idx + 1)
            desc = topic[2].format(city)
            content = f"""
            <h2>{title}</h2>
            <p>{desc}</p>
            <p>مجموعه ما با سال‌ها تجربه در زمینه تامین ملزومات تحریر و نوشت‌افزار مفتخر است با ارائه ضمانت اصالت کالا، بهترین قیمت رقابتی و امکان ثبت سفارش با قابلیت انتخاب رنگ و اولویت ارسال، پاسخگوی نیازهای شما در سراسر کشور باشد.</p>
            <h3>مزایای سفارش از ما:</h3>
            <ul>
                <li>تضمین کمترین قیمت با کیفیت استاندارد</li>
                <li>ارسال فوری با بسته‌بندی ایمن</li>
                <li>امکان انتخاب رنگ‌های متنوع و تعیین اولویت جایگزین</li>
                <li>پشتیبانی ۲۴ ساعته تلفنی و آنلاین</li>
            </ul>
            """
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO pages (title, slug, excerpt, body_content, template_type, is_published, meta_title, meta_description)
                    VALUES (?, ?, ?, ?, 'standard', 1, ?, ?)
                    """,
                    (title, slug, desc, content, f"{title} | فروشگاه ما", desc)
                )
                created += 1
            except Exception:
                pass

    return RedirectResponse(url="/admin/pages", status_code=303)

# ==================== BLOG POSTS ====================

@router.get("/blog")
def blog_posts_list(request: Request):
    """Lists blog posts."""
    user = require_auth(request)
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM blog_posts ORDER BY id DESC").fetchall()

    ctx = get_site_context(request, {
        "title": "مدیریت مقالات وبلاگ / Blog Posts",
        "current_user": user,
        "posts": [dict(r) for r in rows],
    })
    return templates.TemplateResponse(request=request, name="admin/blog_list.html", context=ctx)

@router.get("/blog/new")
def blog_post_new(request: Request):
    """Create new blog post."""
    user = require_auth(request)
    ctx = get_site_context(request, {
        "title": "افزودن مقاله جدید / New Blog Post",
        "current_user": user,
        "post": None,
    })
    return templates.TemplateResponse(request=request, name="admin/blog_edit.html", context=ctx)

@router.get("/blog/{post_id}/edit")
def blog_post_edit(request: Request, post_id: int):
    """Edit blog post."""
    user = require_auth(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM blog_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Blog post not found")

    ctx = get_site_context(request, {
        "title": f"ویرایش مقاله: {row['title']} / Edit Blog Post",
        "current_user": user,
        "post": dict(row),
    })
    return templates.TemplateResponse(request=request, name="admin/blog_edit.html", context=ctx)

@router.post("/blog/save")
def blog_post_save(
    request: Request,
    post_id: Optional[int] = Form(None),
    title: str = Form(...),
    slug: str = Form(...),
    excerpt: str = Form(""),
    content: str = Form(...),
    featured_image: str = Form(""),
    category: str = Form("اخبار و مقالات"),
    tags: str = Form(""),
    author_name: str = Form("مدیریت"),
    is_published: Optional[str] = Form(None),
    meta_title: str = Form(""),
    meta_description: str = Form("")
):
    """Saves blog post."""
    require_auth(request)
    published_val = 1 if is_published else 0

    clean_slug = slug.strip().lower()
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM blog_posts WHERE slug = ?", (clean_slug,)).fetchone()
        if existing and (not post_id or existing["id"] != post_id):
            clean_slug = f"{clean_slug}-{int(time.time())}"

        if post_id:
            conn.execute(
                """
                UPDATE blog_posts SET
                    title = ?, slug = ?, excerpt = ?, content = ?, featured_image = ?,
                    category = ?, tags = ?, author_name = ?, is_published = ?,
                    meta_title = ?, meta_description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    title.strip(), clean_slug, excerpt.strip(), content.strip(),
                    featured_image.strip(), category.strip(), tags.strip(), author_name.strip(),
                    published_val, meta_title.strip(), meta_description.strip(),
                    post_id
                )
            )
        else:
            conn.execute(
                """
                INSERT INTO blog_posts (
                    title, slug, excerpt, content, featured_image,
                    category, tags, author_name, is_published,
                    meta_title, meta_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(), clean_slug, excerpt.strip(), content.strip(),
                    featured_image.strip(), category.strip(), tags.strip(), author_name.strip(),
                    published_val, meta_title.strip(), meta_description.strip()
                )
            )

    return RedirectResponse(url="/admin/blog", status_code=303)

@router.post("/blog/{post_id}/delete")
def blog_post_delete(request: Request, post_id: int):
    """Deletes blog post."""
    require_auth(request)
    with get_db() as conn:
        conn.execute("DELETE FROM blog_posts WHERE id = ?", (post_id,))
    return RedirectResponse(url="/admin/blog", status_code=303)

# ==================== MENUS ====================

@router.get("/menus")
def menus_manager(request: Request):
    """Menu items editor."""
    user = require_auth(request)
    with get_db() as conn:
        header_items = conn.execute("SELECT * FROM menu_items WHERE location = 'header' ORDER BY sort_order ASC, id ASC").fetchall()
        footer_items = conn.execute("SELECT * FROM menu_items WHERE location = 'footer' ORDER BY sort_order ASC, id ASC").fetchall()

    ctx = get_site_context(request, {
        "title": "مدیریت فهرست\u200cها و منو / Menu Navigation",
        "current_user": user,
        "header_items": [dict(m) for m in header_items],
        "footer_items": [dict(m) for m in footer_items],
    })
    return templates.TemplateResponse(request=request, name="admin/menus.html", context=ctx)

@router.post("/menus/save")
def menu_item_save(
    request: Request,
    location: str = Form("header"),
    label: str = Form(...),
    url: str = Form(...),
    sort_order: int = Form(0),
    is_new_tab: Optional[str] = Form(None)
):
    """Adds a menu item."""
    require_auth(request)
    new_tab_val = 1 if is_new_tab else 0
    with get_db() as conn:
        conn.execute(
            "INSERT INTO menu_items (location, label, url, sort_order, is_new_tab) VALUES (?, ?, ?, ?, ?)",
            (location, label.strip(), url.strip(), sort_order, new_tab_val)
        )
    invalidate_navigation_cache()
    return RedirectResponse(url="/admin/menus", status_code=303)

@router.post("/menus/{item_id}/delete")
def menu_item_delete(request: Request, item_id: int):
    """Deletes a menu item."""
    require_auth(request)
    with get_db() as conn:
        conn.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    invalidate_navigation_cache()
    return RedirectResponse(url="/admin/menus", status_code=303)

# ==================== SETTINGS & GLOBAL TOGGLES ====================

@router.get("/settings")
def settings_page(request: Request, saved: bool = False):
    """Site settings, branding, and feature toggles."""
    user = require_auth(request)
    all_settings = get_all_settings()

    ctx = get_site_context(request, {
        "title": "تنظیمات وب\u200cسایت و ویژگی\u200cها / Site Settings",
        "current_user": user,
        "saved": saved,
        "raw_settings": all_settings,
    })
    return templates.TemplateResponse(request=request, name="admin/settings.html", context=ctx)

@router.post("/settings/save")
def settings_save(
    request: Request,
    brand_name: str = Form(""),
    tagline: str = Form(""),
    logo_url: str = Form(""),
    favicon_url: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    address: str = Form(""),
    currency: str = Form("تومان"),
    default_lang: str = Form("fa"),
    rtl_mode: Optional[str] = Form(None),
    footer_about: str = Form(""),
    footer_copyright: str = Form(""),
    global_enable_priority: Optional[str] = Form(None),
    global_enable_color_variants: Optional[str] = Form(None),
):
    """Saves global site settings and master toggles."""
    require_auth(request)

    set_setting("brand_name", brand_name.strip())
    set_setting("tagline", tagline.strip())
    set_setting("logo_url", logo_url.strip())
    set_setting("favicon_url", favicon_url.strip())
    set_setting("phone", phone.strip())
    set_setting("email", email.strip())
    set_setting("address", address.strip())
    set_setting("currency", currency.strip())
    set_setting("default_lang", default_lang.strip())
    set_setting("rtl_mode", "1" if rtl_mode else "0")
    set_setting("footer_about", footer_about.strip())
    set_setting("footer_copyright", footer_copyright.strip())

    # Master feature toggles
    set_setting("global_enable_priority", "1" if global_enable_priority else "0")
    set_setting("global_enable_color_variants", "1" if global_enable_color_variants else "0")

    return RedirectResponse(url="/admin/settings?saved=true", status_code=303)

# ==================== INQUIRIES ====================

@router.get("/inquiries")
def inquiries_list(request: Request):
    """Customer inquiries view."""
    user = require_auth(request)
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM inquiries ORDER BY created_at DESC").fetchall()

    ctx = get_site_context(request, {
        "title": "پیام\u200cها و استعلام\u200cها / Customer Inquiries",
        "current_user": user,
        "inquiries": [dict(r) for r in rows],
    })
    return templates.TemplateResponse(request=request, name="admin/inquiries.html", context=ctx)

@router.post("/inquiries/{inquiry_id}/read")
def inquiry_mark_read(request: Request, inquiry_id: int):
    """Marks inquiry as read."""
    require_auth(request)
    with get_db() as conn:
        conn.execute("UPDATE inquiries SET is_read = 1 WHERE id = ?", (inquiry_id,))
    return RedirectResponse(url="/admin/inquiries", status_code=303)

@router.post("/inquiries/{inquiry_id}/delete")
def inquiry_delete(request: Request, inquiry_id: int):
    """Deletes inquiry."""
    require_auth(request)
    with get_db() as conn:
        conn.execute("DELETE FROM inquiries WHERE id = ?", (inquiry_id,))
    return RedirectResponse(url="/admin/inquiries", status_code=303)

# ==================== MEDIA UPLOAD ====================

@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Uploads media file to static uploads folder."""
    require_auth(request)
    filename = f"{int(time.time())}_{file.filename.replace(' ', '_')}"
    destination = settings.UPLOAD_DIR / filename
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_url = f"/static/uploads/{filename}"
    return JSONResponse({"url": file_url, "filename": filename})
