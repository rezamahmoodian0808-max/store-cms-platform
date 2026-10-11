from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.database import get_db
from app.helpers import get_site_context

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/page/{slug}")
def view_page(request: Request, slug: str):
    """
    Renders any dynamic CMS page by slug.
    This enables easily exceeding 100+ SEO-optimized content pages!
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM pages WHERE slug = ? AND is_published = 1",
            (slug,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Page not found")

        page_data = dict(row)

    ctx = get_site_context(request, {
        "title": page_data.get("meta_title") or page_data["title"],
        "page": page_data,
    })
    return templates.TemplateResponse(request=request, name="page.html", context=ctx)

@router.get("/about")
def about_page(request: Request):
    """About Us page (falls back to /page/about or dedicated template)."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM pages WHERE slug = 'about' AND is_published = 1").fetchone()
    
    page_data = dict(row) if row else {
        "title": "درباره ما / About Us",
        "body_content": "<p>ما متعهد به ارائه بالاترین کیفیت محصولات و برترین تجربه مشتریان هستیم.</p>",
        "meta_title": "درباره ما / About Us",
        "meta_description": "آشنایی با تاریخچه و اهداف فروشگاه ما"
    }
    ctx = get_site_context(request, {
        "title": page_data.get("meta_title") or page_data["title"],
        "page": page_data,
    })
    return templates.TemplateResponse(request=request, name="about.html", context=ctx)

@router.get("/contact")
def contact_page(request: Request, sent: bool = False):
    """Contact Us page with working form and business details."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM pages WHERE slug = 'contact' AND is_published = 1").fetchone()
    page_data = dict(row) if row else None

    ctx = get_site_context(request, {
        "title": "تماس با ما / Contact Us",
        "page": page_data,
        "message_sent": sent
    })
    return templates.TemplateResponse(request=request, name="contact.html", context=ctx)

@router.post("/contact/submit")
def submit_contact(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    subject: str = Form(""),
    message: str = Form(...)
):
    """Handles inquiry submission from contact page."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO inquiries (full_name, email, phone, subject, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (full_name.strip(), email.strip(), phone.strip(), subject.strip(), message.strip())
        )
    return RedirectResponse(url="/contact?sent=true", status_code=303)
