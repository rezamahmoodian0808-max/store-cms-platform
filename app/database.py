import sqlite3
import json
from contextlib import contextmanager
from app.config import settings
from app.cache import cache

def get_connection():
    """
    Creates an optimized SQLite connection with WAL mode, memory cache,
    fast memory mapping, and generous busy timeouts for concurrent workers.
    """
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Detect PythonAnywhere or shared NFS storage where WAL mode locks
    is_pythonanywhere = (
        "PYTHONANYWHERE_DOMAIN" in os.environ 
        or "PYTHONANYWHERE_SITE" in os.environ 
        or os.path.exists("/var/www")
    )
    
    if is_pythonanywhere:
        conn.execute("PRAGMA journal_mode = DELETE;")
        conn.execute("PRAGMA synchronous = NORMAL;")
    else:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA mmap_size = 268435456;") # 256MB memory mapping
    return conn

@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes tables, defaults, and high-performance indexes."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Users table (Admin & Editors)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin', -- 'admin', 'editor'
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Categories
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0
        );
        """)

        # Products
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            sku TEXT DEFAULT '',
            category_id INTEGER,
            price REAL NOT NULL DEFAULT 0.0,
            compare_at_price REAL DEFAULT NULL,
            stock_quantity INTEGER NOT NULL DEFAULT 10,
            is_in_stock INTEGER NOT NULL DEFAULT 1,
            featured_image TEXT DEFAULT '',
            gallery_images TEXT DEFAULT '[]', -- JSON array of image URLs
            short_description TEXT DEFAULT '',
            description TEXT DEFAULT '',
            is_featured INTEGER DEFAULT 0,
            is_published INTEGER DEFAULT 1,

            -- Modular Feature A: Priority / Ordering selection system
            has_priority_system INTEGER DEFAULT 0,
            priority_label_1 TEXT DEFAULT 'انتخاب اولویت اول / Priority 1',
            priority_label_2 TEXT DEFAULT 'انتخاب اولویت دوم / Priority 2',
            priority_options TEXT DEFAULT '[]', -- JSON array: e.g. ["آبی", "مشکی", "سبز", "زرد", "طوسی"]
            priority_helper_text TEXT DEFAULT 'در صورت موجود نبودن اولویت اول، اولویت دوم برای شما ارسال می‌گردد.',

            -- Modular Feature B: Color Variant system
            has_color_variants INTEGER DEFAULT 0,
            color_variants TEXT DEFAULT '[]', -- JSON array of objects: [{"id": "1", "name": "آبی", "hex": "#2563eb", "image": "...", "price": 36000, "sku": "PNT-BLU", "stock": 20}]

            meta_title TEXT DEFAULT '',
            meta_description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        );
        """)

        # CMS Dynamic Pages (supports 100+ pages)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            excerpt TEXT DEFAULT '',
            body_content TEXT DEFAULT '',
            template_type TEXT DEFAULT 'standard', -- standard, fullwidth, landing
            is_published INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            meta_title TEXT DEFAULT '',
            meta_description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Blog Posts
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            excerpt TEXT DEFAULT '',
            content TEXT DEFAULT '',
            featured_image TEXT DEFAULT '',
            category TEXT DEFAULT 'مقالات / Articles',
            tags TEXT DEFAULT '', -- comma separated
            author_name TEXT DEFAULT 'مدیریت / Admin',
            is_published INTEGER DEFAULT 1,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            views_count INTEGER DEFAULT 0,
            meta_title TEXT DEFAULT '',
            meta_description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Navigation Menus
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL DEFAULT 'header', -- 'header', 'footer'
            label TEXT NOT NULL,
            url TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            is_new_tab INTEGER DEFAULT 0
        );
        """)

        # Site Settings (Key-Value)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)

        # Inquiries (Contact Us form submissions)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # High-performance indexes for lightning-fast queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_slug ON products(slug);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_pub_feat ON products(is_published, is_featured, id DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_cat_pub ON products(category_id, is_published, id DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_slug ON pages(slug);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_pub ON pages(is_published, sort_order ASC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_blog_slug ON blog_posts(slug);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_blog_pub_date ON blog_posts(is_published, published_at DESC, id DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_loc ON menu_items(location, sort_order ASC, id ASC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inquiries_unread ON inquiries(is_read, id DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_order ON categories(sort_order ASC, name ASC);")

def get_setting(key: str, default: str = "") -> str:
    """Helper to fetch a single setting value (cached)."""
    settings_dict = get_all_settings()
    return settings_dict.get(key, default)

def set_setting(key: str, value: str):
    """Helper to save or update a setting value, invalidating the settings cache."""
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO site_settings (key, value) VALUES (?, ?)", (key, value))
    cache.delete("all_settings")

def set_multiple_settings(settings_map: dict):
    """Batch updates settings and purges cache."""
    with get_db() as conn:
        for k, v in settings_map.items():
            conn.execute("INSERT OR REPLACE INTO site_settings (key, value) VALUES (?, ?)", (k, str(v)))
    cache.delete("all_settings")

def get_all_settings() -> dict:
    """Helper to fetch all settings as a dict with fast in-memory caching."""
    cached = cache.get("all_settings")
    if cached is not None:
        return cached

    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM site_settings").fetchall()
        settings_dict = {r["key"]: r["value"] for r in rows}

    cache.set("all_settings", settings_dict, ttl=600)
    return settings_dict
