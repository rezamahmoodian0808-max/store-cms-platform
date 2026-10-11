from typing import Optional
from fastapi import APIRouter, HTTPException
from app.database import get_db, get_all_settings
from app.helpers import parse_json_field

router = APIRouter(prefix="/api")

@router.get("/products")
def api_products(category: Optional[str] = None, q: Optional[str] = None):
    """Headless API for product catalog."""
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
        query += " AND (p.title LIKE ? OR p.description LIKE ?)"
        term = f"%{q.strip()}%"
        params.extend([term, term])

    query += " ORDER BY p.id DESC"

    with get_db() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    result = []
    for r in rows:
        item = dict(r)
        item["color_variants"] = parse_json_field(item.get("color_variants"))
        item["priority_options"] = parse_json_field(item.get("priority_options"))
        item["gallery_images"] = parse_json_field(item.get("gallery_images"))
        result.append(item)

    return {"status": "success", "count": len(result), "data": result}

@router.get("/products/{slug}")
def api_product_detail(slug: str):
    """Headless API for single product."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.slug = ? AND p.is_published = 1
            """,
            (slug,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Product not found")

        item = dict(row)
        item["color_variants"] = parse_json_field(item.get("color_variants"))
        item["priority_options"] = parse_json_field(item.get("priority_options"))
        item["gallery_images"] = parse_json_field(item.get("gallery_images"))

    return {"status": "success", "data": item}

@router.get("/pages")
def api_pages():
    """Headless API for CMS pages (100+ pages accessible)."""
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, slug, excerpt, template_type, is_published, sort_order FROM pages WHERE is_published = 1 ORDER BY sort_order ASC").fetchall()
    return {"status": "success", "count": len(rows), "data": [dict(r) for r in rows]}

@router.get("/pages/{slug}")
def api_page_detail(slug: str):
    """Headless API for single CMS page."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM pages WHERE slug = ? AND is_published = 1", (slug,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Page not found")
    return {"status": "success", "data": dict(row)}

@router.get("/blog")
def api_blog(category: Optional[str] = None):
    """Headless API for blog posts."""
    query = "SELECT * FROM blog_posts WHERE is_published = 1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY published_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return {"status": "success", "count": len(rows), "data": [dict(r) for r in rows]}

@router.get("/settings")
def api_settings():
    """Headless API for site branding and global feature toggles."""
    all_settings = get_all_settings()
    return {"status": "success", "data": all_settings}
