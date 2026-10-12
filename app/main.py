import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.config import settings
from app.database import init_db
from app.helpers import get_site_context
from app.routers import storefront, pages, blog, admin, api

class SecurityAndPerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Enforce HTTPS if configured or if client header indicates insecure behind proxy
        if settings.FORCE_HTTPS:
            forwarded_proto = request.headers.get("x-forwarded-proto", "")
            if forwarded_proto == "http" or request.url.scheme == "http":
                secure_url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(secure_url), status_code=301)

        response = await call_next(request)

        # Standard SSL and security headers
        if settings.FORCE_HTTPS:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-DNS-Prefetch-Control"] = "on"

        # Static assets caching header
        if request.url.path.startswith("/static"):
            response.headers["Cache-Control"] = "public, max-age=86400, immutable"

        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and tables
    init_db()
    yield

app = FastAPI(
    title="Modern Business & E-Commerce CMS",
    description="High-Performance multi-worker CMS website with modular Priority & Color Variant systems",
    version="2.1.0",
    lifespan=lifespan
)

# GZip compression for responses > 500 bytes (saves bandwidth and accelerates TTFB)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(SecurityAndPerformanceMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Register Routers
app.include_router(storefront.router)
app.include_router(pages.router)
app.include_router(blog.router)
app.include_router(admin.router)
app.include_router(api.router)

# Jinja2 Templates optimized configuration
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)
templates.env.auto_reload = settings.DEBUG
templates.env.trim_blocks = True
templates.env.lstrip_blocks = True

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    detail_msg = getattr(exc, "detail", "صفحه مورد نظر یافت نشد.")
    page_data = {
        "title": "صفحه مورد نظر یافت نشد (۴۰۴)",
        "excerpt": "متأسفانه صفحه‌ای که به دنبال آن بودید در سیستم پیدا نشد.",
        "body_content": f"<p class='text-center py-6 text-slate-500'>{detail_msg}</p><div class='text-center mt-4'><a href='/' class='inline-block px-6 py-2.5 rounded-xl bg-blue-600 text-white font-bold text-xs hover:bg-blue-700 transition-colors'>بازگشت به صفحه اصلی فروشگاه</a></div>",
        "meta_title": "صفحه مورد نظر یافت نشد (خطای ۴۰۴)",
        "meta_description": "صفحه مورد نظر یافت نشد."
    }
    ctx = get_site_context(request, {
        "title": page_data["title"],
        "detail": detail_msg,
        "page": page_data
    })
    return templates.TemplateResponse(request=request, name="page.html", context=ctx, status_code=404)
