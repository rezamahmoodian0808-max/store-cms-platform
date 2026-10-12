from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from app.database import get_db
from app.helpers import get_site_context
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)

@router.get("/blog")
def blog_list(
    request: Request,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    q: Optional[str] = None
):
    """Blog posts listing with category, tag, and search filters."""
    query = "SELECT * FROM blog_posts WHERE is_published = 1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")

    if q:
        query += " AND (title LIKE ? OR content LIKE ? OR excerpt LIKE ?)"
        term = f"%{q.strip()}%"
        params.extend([term, term, term])

    query += " ORDER BY published_at DESC, id DESC"

    with get_db() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        # Fetch distinct categories and tags for sidebar
        all_cats = conn.execute(
            "SELECT DISTINCT category FROM blog_posts WHERE is_published = 1 AND category != ''"
        ).fetchall()

    posts = [dict(r) for r in rows]
    categories = [r["category"] for r in all_cats]

    ctx = get_site_context(request, {
        "title": "وبلاگ و مقالات / Blog & News",
        "posts": posts,
        "selected_category": category,
        "selected_tag": tag,
        "search_query": q or "",
        "categories_list": categories,
    })
    return templates.TemplateResponse(request=request, name="blog_list.html", context=ctx)

@router.get("/blog/{slug}")
def blog_detail(request: Request, slug: str):
    """Single blog post view with author, published date, related posts, and view counter."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM blog_posts WHERE slug = ? AND is_published = 1",
            (slug,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Blog post not found")

        post = dict(row)

        # Increment views
        conn.execute("UPDATE blog_posts SET views_count = views_count + 1 WHERE id = ?", (post["id"],))

        # Related posts in same category
        related = conn.execute(
            """
            SELECT * FROM blog_posts
            WHERE is_published = 1 AND id != ? AND category = ?
            ORDER BY published_at DESC LIMIT 3
            """,
            (post["id"], post["category"])
        ).fetchall()

    tags_list = [t.strip() for t in post["tags"].split(",") if t.strip()] if post.get("tags") else []

    ctx = get_site_context(request, {
        "title": post.get("meta_title") or post["title"],
        "post": post,
        "tags_list": tags_list,
        "related_posts": [dict(r) for r in related],
    })
    return templates.TemplateResponse(request=request, name="blog_detail.html", context=ctx)
