import os
import sys
from pathlib import Path
import pytest
from starlette.testclient import TestClient

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.config import settings
from app.database import get_db, get_setting, set_setting, get_all_settings
from app.auth import hash_password, verify_password, create_session_token, decode_session_token
from app.cache import cache
from app.helpers import get_cached_navigation, invalidate_navigation_cache
from seed import seed_database

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    seed_database()

@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)

def test_auth_crypto():
    pw = "SecretTest123"
    pw_hash, salt = hash_password(pw)
    assert verify_password(pw, pw_hash, salt) is True
    assert verify_password("WrongPw", pw_hash, salt) is False

    # Test Session Token
    payload = {"user_id": 1, "role": "admin"}
    token = create_session_token(payload)
    decoded = decode_session_token(token)
    assert decoded is not None
    assert decoded["user_id"] == 1
    assert decoded["role"] == "admin"
    assert decode_session_token("invalid.token") is None

def test_cache_functionality():
    cache.clear()
    assert cache.get("test_key") is None
    cache.set("test_key", {"data": 123}, ttl=10)
    assert cache.get("test_key") == {"data": 123}
    cache.delete("test_key")
    assert cache.get("test_key") is None

def test_navigation_caching_and_invalidation():
    invalidate_navigation_cache()
    h1, f1, c1 = get_cached_navigation()
    assert isinstance(h1, list)
    assert isinstance(f1, list)
    assert isinstance(c1, list)

    # Calling again hits cache
    h2, f2, c2 = get_cached_navigation()
    assert h1 == h2
    assert f1 == f2
    assert c1 == c2

def test_storefront_home(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "صفحه اصلی" in res.text

def test_storefront_catalog(client):
    res = client.get("/catalog")
    assert res.status_code == 200
    assert "کاتالوگ محصولات" in res.text

    # Search filter
    res_search = client.get("/catalog?q=پنتر")
    assert res_search.status_code == 200
    assert "پنتر" in res_search.text

    # Sort filter
    res_sort = client.get("/catalog?sort=price_asc")
    assert res_sort.status_code == 200

def test_product_detail_priority_product(client):
    # Panter Sharpener (Priority Only)
    res = client.get("/product/panter-sharpener-handy-ps-104")
    assert res.status_code == 200
    assert "پنتر تراش handy ps-104" in res.text
    assert "سیستم اولویت" in res.text
    assert "انتخاب اولویت اول" in res.text

def test_product_detail_color_variants_product(client):
    # Ariapen Persia (Color Variants Only)
    res = client.get("/product/persia-whiteboard-marker")
    assert res.status_code == 200
    assert "ماژیک وایت‌برد پرشیا" in res.text
    assert "color-swatch-btn" in res.text

def test_product_detail_both_features(client):
    # Arya Spiral Notebook (Both)
    res = client.get("/product/arya-notebook-100-sheets-metallic")
    assert res.status_code == 200
    assert "دفتر یادداشت سیمی ۱۰۰ برگ آریا" in res.text
    assert "سیستم اولویت" in res.text
    assert "color-swatch-btn" in res.text

def test_product_detail_standard_product(client):
    # Kangaro Stapler (Neither)
    res = client.get("/product/kangaro-stapler-ds-45l")
    assert res.status_code == 200
    assert "منگنه رومیزی استیل کانگرو" in res.text

def test_product_detail_404(client):
    res = client.get("/product/non-existent-product-slug")
    assert res.status_code == 404
    assert "یافت نشد" in res.text

def test_pages_routes(client):
    res_about = client.get("/about")
    assert res_about.status_code == 200
    assert "درباره ما" in res_about.text

    res_contact = client.get("/contact")
    assert res_contact.status_code == 200
    assert "تماس با ما" in res_contact.text

def test_blog_routes(client):
    res_blog = client.get("/blog")
    assert res_blog.status_code == 200
    assert "وبلاگ" in res_blog.text

    # Single post
    res_post = client.get("/blog/ergonomic-pencil-sharpener-buying-guide")
    assert res_post.status_code == 200
    assert "راهنمای جامع خرید تراش ارگونومیک" in res_post.text

def test_contact_inquiry_submission(client):
    data = {
        "full_name": "علی رضایی",
        "email": "ali@example.com",
        "phone": "09120000000",
        "subject": "استعلام خرید عمده",
        "message": "سلام، لطفاً کاتالوگ قیمت عمده را ارسال فرمایید."
    }
    res = client.post("/contact/submit", data=data)
    assert res.status_code == 303
    assert "/contact?sent=true" in res.headers["location"]

    # Verify persisted in database
    with get_db() as conn:
        inquiry = conn.execute("SELECT * FROM inquiries WHERE email = ?", (data["email"],)).fetchone()
        assert inquiry is not None
        assert inquiry["full_name"] == data["full_name"]

def test_api_endpoints(client):
    res = client.get("/api/products")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["status"] == "success"
    assert len(json_data["data"]) >= 4

    # Single product API
    res_p = client.get("/api/products/persia-whiteboard-marker")
    assert res_p.status_code == 200
    p_data = res_p.json()
    assert p_data["status"] == "success"
    assert p_data["data"]["slug"] == "persia-whiteboard-marker"
    assert len(p_data["data"]["color_variants"]) > 0

def test_admin_auth_flow(client):
    # GET login page
    res = client.get("/admin/login")
    assert res.status_code == 200
    assert "ورود به پنل مدیریت" in res.text

    # Unauthorized access to /admin redirects to login
    res_protected = client.get("/admin")
    assert res_protected.status_code == 303
    assert "/admin/login" in res_protected.headers["location"]

    # Invalid login
    res_fail = client.post("/admin/login", data={"email": "wrong@example.com", "password": "wrong"})
    assert res_fail.status_code == 303
    assert "error=invalid_credentials" in res_fail.headers["location"]

    # Valid login
    res_ok = client.post("/admin/login", data={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
    assert res_ok.status_code == 303
    assert res_ok.headers["location"] == "/admin"
    assert "session_token" in res_ok.headers.get("set-cookie", "")

def test_gzip_compression_header(client):
    # Request with Accept-Encoding: gzip
    res = client.get("/", headers={"accept-encoding": "gzip"})
    assert res.status_code == 200
    if len(res.content) >= 500:
        assert res.headers.get("content-encoding") == "gzip"

def test_concurrent_db_reads():
    import concurrent.futures
    def read_operation():
        with get_db() as conn:
            return conn.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: read_operation(), range(20)))

    assert len(results) == 20
    assert all(r > 0 for r in results)

def test_settings_update_cache_invalidation():
    # Set a test setting
    set_setting("custom_brand_test", "FastAPI Pro Store")
    assert get_setting("custom_brand_test") == "FastAPI Pro Store"

    # Verify cached
    all_s = get_all_settings()
    assert all_s.get("custom_brand_test") == "FastAPI Pro Store"

    # Update setting
    set_setting("custom_brand_test", "FastAPI Pro Store Updated")
    assert get_setting("custom_brand_test") == "FastAPI Pro Store Updated"

def test_product_detail_variant_id_selection(client):
    # Request specific valid variant ID (748 is Black / مشکی)
    res = client.get("/product/persia-whiteboard-marker?vid=748")
    assert res.status_code == 200
    assert "مشکی" in res.text
    # Verify selectedColorId and selectedColorName initialized with the chosen variant
    assert "selectedColorId: '748'" in res.text
    assert "selectedColorName: 'مشکی / Black'" in res.text

    # Request invalid/non-existent variant ID - gracefully degrades without 500 error
    res_invalid = client.get("/product/persia-whiteboard-marker?vid=999999")
    assert res_invalid.status_code == 200

def test_pydantic_models_validation():
    from app.models import ProductCreate, ColorVariant, BlogPostCreate
    v = ColorVariant(id="10", name="قرمز", hex="#ef4444", price=50000.0)
    assert v.name == "قرمز"
    assert v.hex == "#ef4444"

    p = ProductCreate(
        title="تست مدل محصول",
        slug="test-model-product",
        price=120000.0,
        has_color_variants=True,
        color_variants=[v]
    )
    assert p.slug == "test-model-product"
    assert len(p.color_variants) == 1

def test_admin_product_save_and_crud(client):
    # Log in as admin
    login_res = client.post("/admin/login", data={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
    assert login_res.status_code == 303
    cookies = login_res.cookies

    # Create new product with priority and color variants
    import json
    colors = [{"id": "901", "name": "نقره‌ای", "hex": "#cbd5e1", "price": 85000, "sku": "TST-SLV", "stock": 15}]
    prod_data = {
        "title": "خودکار لوکس تست چندورکری",
        "slug": "luxury-pen-test-worker",
        "sku": "TST-LX-01",
        "price": 85000,
        "stock_quantity": 25,
        "is_published": "1",
        "has_priority_system": "1",
        "priority_label_1": "اولویت اول تست",
        "priority_label_2": "اولویت دوم تست",
        "priority_options_raw": "نقره‌ای\nطلایی",
        "has_color_variants": "1",
        "color_variants_json": json.dumps(colors)
    }
    save_res = client.post("/admin/products/save", data=prod_data, cookies=cookies)
    assert save_res.status_code == 303

    # Verify created product in storefront
    store_res = client.get("/product/luxury-pen-test-worker")
    assert store_res.status_code == 200
    assert "خودکار لوکس تست چندورکری" in store_res.text
    assert "اولویت اول تست" in store_res.text
    assert "نقره‌ای" in store_res.text

def test_custom_404_handler(client):
    res = client.get("/this-route-definitely-does-not-exist-at-all")
    assert res.status_code == 404
    assert "صفحه مورد نظر یافت نشد" in res.text

