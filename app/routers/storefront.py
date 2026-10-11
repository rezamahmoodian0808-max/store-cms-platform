import json
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from app.database import get_db
from app.helpers import get_site_context, parse_json_field

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
def home(request: Request):
    """Homepage with hero, featured products, categories, and recent blog posts."""
    with get_db() as conn:
        featured_products = conn.execute(
            """
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.is_published = 1 AND p.is_featured = 1
            ORDER BY p.id DESC LIMIT 8
            """
        ).fetchall()

        latest_products = conn.execute(
            """
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.is_published = 1
            ORDER BY p.id DESC LIMIT 8
            """
        ).fetchall()

        recent_posts = conn.execute(
            """
            SELECT * FROM blog_posts
            WHERE is_published = 1
            ORDER BY published_at DESC, id DESC LIMIT 3
            """
        ).fetchall()

    featured_list = []
    for p in featured_products:
        item = dict(p)
        item["color_variants"] = parse_json_field(item.get("color_variants"))
        item["priority_options"] = parse_json_field(item.get("priority_options"))
        item["gallery_images"] = parse_json_field(item.get("gallery_images"))
        featured_list.append(item)

    latest_list = []
    for p in latest_products:
        item = dict(p)
        item["color_variants"] = parse_json_field(item.get("color_variants"))
        item["priority_options"] = parse_json_field(item.get("priority_options"))
        item["gallery_images"] = parse_json_field(item.get("gallery_images"))
        latest_list.append(item)

    ctx = get_site_context(request, {
        "title": "صفحه اصلی / Home",
        "featured_products": featured_list,
        "latest_products": latest_list,
        "recent_posts": [dict(p) for p in recent_posts],
    })
    return templates.TemplateResponse(request=request, name="home.html", context=ctx)

@router.get("/catalog")
def catalog(
    request: Request,
    category: Optional[str] = None,
    sort: Optional[str] = "newest",
    q: Optional[str] = None
):
    """Product catalog with search, filtering, and sorting."""
    query = """
        SELECT p.*, c.name as category_name, c.slug as category_slug
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.is_published = 1
    """
    params = []

    if category:
        query += " AND (c.slug = ? OR c.name = ?)"
        params.extend([category, category])

    if q:
        query += " AND (p.title LIKE ? OR p.description LIKE ? OR p.sku LIKE ?)"
        term = f"%{q.strip()}%"
        params.extend([term, term, term])

    if sort == "price_asc":
        query += " ORDER BY p.price ASC"
    elif sort == "price_desc":
        query += " ORDER BY p.price DESC"
    else:
        query += " ORDER BY p.id DESC"

    with get_db() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    products = []
    for r in rows:
        item = dict(r)
        item["color_variants"] = parse_json_field(item.get("color_variants"))
        item["priority_options"] = parse_json_field(item.get("priority_options"))
        item["gallery_images"] = parse_json_field(item.get("gallery_images"))
        products.append(item)

    ctx = get_site_context(request, {
        "title": "کاتالوگ محصولات / Product Catalog",
        "products": products,
        "selected_category": category,
        "selected_sort": sort,
        "search_query": q or "",
        "total_results": len(products),
    })
    return templates.TemplateResponse(request=request, name="catalog.html", context=ctx)

@router.get("/category/{slug}")
def category_view(request: Request, slug: str):
    """Shortcut redirect or direct view for a category."""
    return catalog(request=request, category=slug)

@router.get("/product/{slug}")
def product_detail(request: Request, slug: str, vid: Optional[str] = None):
    """
    Product detail page supporting modular Priority System and Color Swatches.
    """
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT p.*, c.name as category_name, c.slug as category_slug
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.slug = ? AND p.is_published = 1
            """,
            (slug,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Product not found")

        product = dict(row)
        product["color_variants"] = parse_json_field(product.get("color_variants"))
        product["priority_options"] = parse_json_field(product.get("priority_options"))
        product["gallery_images"] = parse_json_field(product.get("gallery_images"))

        # Related products in same category
        related = conn.execute(
            """
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.is_published = 1 AND p.id != ? AND (p.category_id = ? OR ? IS NULL)
            ORDER BY p.id DESC LIMIT 4
            """,
            (product["id"], product["category_id"], product["category_id"])
        ).fetchall()

    related_list = []
    for r in related:
        item = dict(r)
        item["color_variants"] = parse_json_field(item.get("color_variants"))
        item["priority_options"] = parse_json_field(item.get("priority_options"))
        item["gallery_images"] = parse_json_field(item.get("gallery_images"))
        related_list.append(item)

    # Pre-select variant if requested via ?vid=...
    selected_variant = None
    if vid and product["color_variants"]:
        for v in product["color_variants"]:
            if str(v.get("id")) == str(vid):
                selected_variant = v
                break

    ctx = get_site_context(request, {
        "title": product.get("meta_title") or product["title"],
        "product": product,
        "selected_variant": selected_variant,
        "initial_vid": vid or (product["color_variants"][0]["id"] if product["color_variants"] else ""),
        "related_products": related_list,
    })
    return templates.TemplateResponse(request=request, name="product_detail.html", context=ctx)
