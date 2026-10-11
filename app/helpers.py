import json
from typing import Dict, Any, Optional, List
from fastapi import Request
from app.database import get_db, get_all_settings
from app.auth import get_current_user_from_request
from app.cache import cache

def parse_json_field(val: Any, default: Any = None) -> Any:
    """Safely decodes JSON strings or returns fallback."""
    if default is None:
        default = []
    if not val:
        return default
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default

def format_price(amount: Optional[float], currency: str = "تومان") -> str:
    """Formats numeric price with thousands comma separator."""
    if amount is None or amount == "":
        return ""
    try:
        val = int(amount) if float(amount).is_integer() else float(amount)
        formatted = f"{val:,.0f}" if isinstance(val, int) else f"{val:,.2f}"
        return f"{formatted} {currency}"
    except Exception:
        return f"{amount} {currency}"

def get_cached_navigation():
    """Fetches header & footer menus and categories with in-memory caching."""
    header_menu = cache.get("header_menu")
    footer_menu = cache.get("footer_menu")
    categories = cache.get("categories_menu")

    if header_menu is None or footer_menu is None or categories is None:
        with get_db() as conn:
            h_rows = conn.execute(
                "SELECT * FROM menu_items WHERE location = 'header' ORDER BY sort_order ASC, id ASC"
            ).fetchall()
            f_rows = conn.execute(
                "SELECT * FROM menu_items WHERE location = 'footer' ORDER BY sort_order ASC, id ASC"
            ).fetchall()
            c_rows = conn.execute(
                "SELECT * FROM categories ORDER BY sort_order ASC, name ASC"
            ).fetchall()

            header_menu = [dict(m) for m in h_rows]
            footer_menu = [dict(m) for m in f_rows]
            categories = [dict(c) for c in c_rows]

            cache.set("header_menu", header_menu, ttl=600)
            cache.set("footer_menu", footer_menu, ttl=600)
            cache.set("categories_menu", categories, ttl=600)

    return header_menu, footer_menu, categories

def invalidate_navigation_cache():
    """Clears cached menu and category structures upon admin updates."""
    cache.delete("header_menu")
    cache.delete("footer_menu")
    cache.delete("categories_menu")

def get_site_context(request: Request, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Provides high-performance standard layout context: cached settings, menus, active user, request."""
    settings_dict = get_all_settings()

    # Defaults if settings not yet populated
    defaults = {
        "brand_name": "فروشگاه مدرن / Modern Store",
        "tagline": "محصولات باکیفیت و نوشت‌افزار مدرن",
        "logo_url": "",
        "favicon_url": "",
        "phone": "021-88889999",
        "email": "info@example.com",
        "address": "تهران، خیابان ولیعصر، پلاک ۱۰۰",
        "currency": "تومان",
        "default_lang": "fa",
        "rtl_mode": "1",
        "global_enable_priority": "1",
        "global_enable_color_variants": "1",
        "footer_about": "ما ارائه دهنده برترین محصولات و نوشت‌افزار با کیفیت استثنایی و خدمات مشتریان پاسخگو هستیم.",
        "footer_copyright": "© ۲۰۲۶ تمامی حقوق محفوظ است."
    }
    for k, v in defaults.items():
        if k not in settings_dict or not settings_dict[k]:
            settings_dict[k] = v

    header_menu, footer_menu, categories = get_cached_navigation()
    user = get_current_user_from_request(request)

    ctx = {
        "request": request,
        "settings": settings_dict,
        "header_menu": header_menu,
        "footer_menu": footer_menu,
        "categories": categories,
        "current_user": user,
        "format_price": format_price,
        "parse_json": parse_json_field,
    }

    if extra:
        ctx.update(extra)

    return ctx
