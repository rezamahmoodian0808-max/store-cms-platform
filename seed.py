import sys
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.database import init_db, get_db, set_setting
from app.auth import hash_password
from app.config import settings

def seed_database():
    print("[*] Initializing Database Schema...")
    init_db()

    with get_db() as conn:
        # Check if already seeded
        existing_admin = conn.execute("SELECT id FROM users WHERE email = ?", (settings.ADMIN_EMAIL,)).fetchone()
        if existing_admin:
            print("[*] Admin user already exists. Re-verifying seed data...")
        else:
            print("[+] Seeding Administrator and Editor Accounts...")
            pw_hash, salt = hash_password(settings.ADMIN_PASSWORD)
            conn.execute(
                """
                INSERT INTO users (email, password_hash, salt, full_name, role, is_active)
                VALUES (?, ?, ?, ?, 'admin', 1)
                """,
                (settings.ADMIN_EMAIL, pw_hash, salt, settings.ADMIN_NAME)
            )

            editor_hash, editor_salt = hash_password("editor123456")
            conn.execute(
                """
                INSERT INTO users (email, password_hash, salt, full_name, role, is_active)
                VALUES (?, ?, ?, 'سارا کریمی (محرر محتوا)', 'editor', 1)
                """,
                ("editor@example.com", editor_hash, editor_salt)
            )

        # 1. Categories
        print("[+] Seeding Categories...")
        categories_data = [
            ("تراش و پاک‌کن", "sharpeners-and-erasers", "انواع تراش رومیزی، مخزن‌دار، فانتزی و پاک‌کن‌های غیرسمی"),
            ("ماژیک و علامت‌گذار", "markers-and-highlighters", "ماژیک وایت‌برد، هایلایترهای پاستلی و ماژیک‌های نقاشی"),
            ("خودکار و روان‌نویس", "pens-and-fineliners", "خودکارهای ارگونومیک، روان‌نویس‌های نوک‌نمدی و خودنویس"),
            ("دفتر و کاغذ", "notebooks-and-paper", "دفاتر سیمی، کلاسور، کاغذ یادداشت و برگه‌های طراحی"),
            ("ملزومات اداری و بایگانی", "office-supplies", "منگنه، پانچ، گیره کاغذ، زونکن و ارگانایزرهای رومیزی"),
        ]
        for name, slug, desc in categories_data:
            conn.execute(
                """
                INSERT OR IGNORE INTO categories (name, slug, description)
                VALUES (?, ?, ?)
                """,
                (name, slug, desc)
            )

        # Get category IDs
        cat_map = {row["slug"]: row["id"] for row in conn.execute("SELECT id, slug FROM categories").fetchall()}

        # 2. Products demonstrating all 4 configurations:
        # A) Priority System ONLY (Panter sharpener ref)
        # B) Color Variants ONLY (Ariapen marker ref)
        # C) BOTH Priority AND Color Variants
        # D) NEITHER (Simple standard product)
        print("[+] Seeding Sample Products with Modular Variants & Priorities...")

        products_data = [
            # Product 1: Priority ONLY (Ref 1: Neveshtafzar Moadel)
            {
                "title": "پنتر تراش handy ps-104 رنگ فانتزی",
                "slug": "panter-sharpener-handy-ps-104",
                "sku": "PNT-PS104",
                "category_id": cat_map.get("sharpeners-and-erasers"),
                "price": 36000.0,
                "compare_at_price": 42000.0,
                "stock_quantity": 87,
                "featured_image": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?auto=format&fit=crop&w=800&q=80",
                "gallery_images": [
                    "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?auto=format&fit=crop&w=800&q=80"
                ],
                "short_description": "دارای تیغه بادوام SK با کیفیت تراشیدن مطلوب، طراحی ارگونومیک برای استفاده آسان، بدنه با متریال آنتی باکتریال.",
                "description": """
                <p><strong>تراش پنتر مدل Handy PS-104</strong> یکی از محبوب‌ترین تراش‌های مخزن‌دار فانتزی موجود در بازار است.</p>
                <h3>ویژگی‌های کلیدی:</h3>
                <ul>
                    <li>دارای تیغه فوق‌العاده برنده از جنس فولاد ضدزنگ SK ساخت ژاپن</li>
                    <li>مخزن شفاف و با گنجایش مناسب برای نگهداری براده‌های مداد</li>
                    <li>طراحی ارگونومیک و ضدلغزش دست هنگام تراشیدن مداد</li>
                    <li>موجود در پنج رنگ جذاب فانتزی (آبی، صورتی، سبز، زرد و طوسی)</li>
                </ul>
                <p>شما می‌توانید اولویت اول و دوم رنگ دلخواه خود را مشخص کنید تا در صورت اتمام موجودی رنگ اول، رنگ جایگزین برای شما ارسال شود.</p>
                """,
                "is_featured": 1,
                "is_published": 1,
                "has_priority_system": 1,
                "priority_label_1": "انتخاب اولویت اول:",
                "priority_label_2": "انتخاب اولویت دوم:",
                "priority_options": ["آبی", "مشکی", "سبز", "زرد", "طوسی", "صورتی", "بنفش"],
                "priority_helper_text": "در صورت موجود نبودن رنگ‌های دلخواه شما، پشتیبانی برای هماهنگی با شما تماس خواهد گرفت.",
                "has_color_variants": 0,
                "color_variants": [],
                "meta_title": "پنتر تراش handy ps-104 رنگ فانتزی - خرید اینترنتی با اولویت رنگ",
                "meta_description": "خرید تراش فانتزی پنتر handy ps 104 با تیغه ژاپنی SK و امکان انتخاب اولویت اول و دوم رنگ ارسال."
            },

            # Product 2: Color Variants ONLY (Ref 2: Ariapen Persia Marker)
            {
                "title": "ماژیک وایت‌برد پرشیا (Persia Whiteboard Marker)",
                "slug": "persia-whiteboard-marker",
                "sku": "PRS-WB01",
                "category_id": cat_map.get("markers-and-highlighters"),
                "price": 28000.0,
                "compare_at_price": 32000.0,
                "stock_quantity": 120,
                "featured_image": "https://images.unsplash.com/photo-1585336261026-68153b6fa03d?auto=format&fit=crop&w=800&q=80",
                "gallery_images": [
                    "https://images.unsplash.com/photo-1585336261026-68153b6fa03d?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?auto=format&fit=crop&w=800&q=80"
                ],
                "short_description": "جوهر با فرمولاسیون اختصاصی بدون بو و اثر لکه بر روی تخته، نوک نمدی گرد و روان با ماندگاری طولانی.",
                "description": """
                <p><strong>ماژیک وایت‌برد پرشیا (Persia)</strong> انتخابی حرفه‌ای برای مدارس، دانشگاه‌ها، ادارات و جلسات پرزنتیشن است.</p>
                <h3>مزایا:</h3>
                <ul>
                    <li>قابلیت پاک‌شوندگی بسیار آسان با تخته‌پاک‌کن بدون بر جای ماندن رد و سایه</li>
                    <li>جوهر الکلی بی بو (Low Odor) مناسب برای استفاده در محیط‌های بسته</li>
                    <li>نوک گرد مقاوم در برابر فشار دست با ضخامت نوشتاری ۲ تا ۳ میلی‌متر</li>
                </ul>
                <p>جهت انتخاب رنگ، بر روی سواچ‌های رنگی زیر کلیک کنید تا مشخصات و تصویر رنگ مربوطه به صورت زنده تغییر کند.</p>
                """,
                "is_featured": 1,
                "is_published": 1,
                "has_priority_system": 0,
                "priority_label_1": "",
                "priority_label_2": "",
                "priority_options": [],
                "priority_helper_text": "",
                "has_color_variants": 1,
                "color_variants": [
                    {"id": "747", "name": "آبی / Blue", "hex": "#1d4ed8", "image": "https://images.unsplash.com/photo-1585336261026-68153b6fa03d?auto=format&fit=crop&w=800&q=80", "price": 28000.0, "sku": "PRS-WB-BLU-747", "stock": 45},
                    {"id": "748", "name": "مشکی / Black", "hex": "#18181b", "image": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?auto=format&fit=crop&w=800&q=80", "price": 28000.0, "sku": "PRS-WB-BLK-748", "stock": 50},
                    {"id": "749", "name": "قرمز / Red", "hex": "#dc2626", "image": "https://images.unsplash.com/photo-1586075010923-2dd4570fb338?auto=format&fit=crop&w=800&q=80", "price": 28000.0, "sku": "PRS-WB-RED-749", "stock": 30},
                    {"id": "750", "name": "سبز / Green", "hex": "#16a34a", "image": "https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?auto=format&fit=crop&w=800&q=80", "price": 28000.0, "sku": "PRS-WB-GRN-750", "stock": 25}
                ],
                "meta_title": "ماژیک وایت برد پرشیا persia | خرید با پالت رنگ متنوع",
                "meta_description": "خرید ماژیک وایت برد پرشیا اصل با قابلیت انتخاب آنلاین رنگ آبی، مشکی، قرمز و سبز با بهترین قیمت."
            },

            # Product 3: BOTH Priority AND Color Variants
            {
                "title": "دفتر یادداشت سیمی ۱۰۰ برگ آریا (جلد متالیک)",
                "slug": "arya-notebook-100-sheets-metallic",
                "sku": "ARY-NB100",
                "category_id": cat_map.get("notebooks-and-paper"),
                "price": 65000.0,
                "compare_at_price": 75000.0,
                "stock_quantity": 40,
                "featured_image": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=800&q=80",
                "gallery_images": [
                    "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=800&q=80"
                ],
                "short_description": "کاغذ ۸۰ گرمی خط‌دار با سیم دوبل آبکاری شده، جلد سخت پلاستیکی با روکش متالیک ضدخش.",
                "description": "<p>دفتر ۱۰۰ برگ سیمی آریا با کاغذهای استاندارد باکیفیت و خط‌کشی خوانا، مناسب دانشجویان و دانش‌آموزان.</p>",
                "is_featured": 1,
                "is_published": 1,
                "has_priority_system": 1,
                "priority_label_1": "اولویت طرح انتخابی اول:",
                "priority_label_2": "اولویت طرح انتخابی دوم (جایگزین):",
                "priority_options": ["طرح کهکشان", "طرح مینیمال خطی", "طرح برگ استوایی", "طرح هندسی"],
                "priority_helper_text": "لطفاً اولویت طرح جلد را تعیین فرمایید.",
                "has_color_variants": 1,
                "color_variants": [
                    {"id": "801", "name": "رزگلد متالیک", "hex": "#e0a899", "image": "", "price": 68000.0, "sku": "ARY-RG-801", "stock": 15},
                    {"id": "802", "name": "نقره‌ای مات", "hex": "#94a3b8", "image": "", "price": 65000.0, "sku": "ARY-SL-802", "stock": 20},
                    {"id": "803", "name": "طلایی شامپاینی", "hex": "#d4af37", "image": "", "price": 68000.0, "sku": "ARY-GL-803", "stock": 12}
                ],
                "meta_title": "دفتر یادداشت سیمی ۱۰۰ برگ آریا با انتخاب رنگ و طرح",
                "meta_description": "خرید آنلاین دفتر سیمی ۱۰۰ برگ با کاغذ اعلا و سیستم انتخاب رنگ و اولویت طرح."
            },

            # Product 4: NEITHER (Simple standard product)
            {
                "title": "منگنه رومیزی استیل کانگرو Kangaro DS-45L",
                "slug": "kangaro-stapler-ds-45l",
                "sku": "KNG-ST45",
                "category_id": cat_map.get("office-supplies"),
                "price": 195000.0,
                "compare_at_price": 220000.0,
                "stock_quantity": 30,
                "featured_image": "https://images.unsplash.com/photo-1589363460779-cd717d77864e?auto=format&fit=crop&w=800&q=80",
                "gallery_images": [
                    "https://images.unsplash.com/photo-1589363460779-cd717d77864e?auto=format&fit=crop&w=800&q=80"
                ],
                "short_description": "بدنه تمام فلزی، مکانیزم اهرمی روان، ظرفیت دوخت تا ۳۰ برگ کاغذ ۸۰ گرم به طور همزمان.",
                "description": "<p>دستگاه منگنه اداری با دوام فوق‌العاده ساخت کمپانی معتبر کانگرو، مناسب برای بایگانی اداری و استفاده روزمره.</p>",
                "is_featured": 0,
                "is_published": 1,
                "has_priority_system": 0,
                "priority_label_1": "",
                "priority_label_2": "",
                "priority_options": [],
                "priority_helper_text": "",
                "has_color_variants": 0,
                "color_variants": [],
                "meta_title": "منگنه رومیزی استیل کانگرو Kangaro DS-45L",
                "meta_description": "خرید منگنه اداری کانگرو اصل با بدنه مستحکم فولادی و گارانتی اصالت کالا."
            },

            # Product 5: Color variants (Highlighter set)
            {
                "title": "هایلایتر پاستلی استابیلو مدل Boss Original Pastel",
                "slug": "stabilo-boss-pastel-highlighter",
                "sku": "STB-BSS01",
                "category_id": cat_map.get("markers-and-highlighters"),
                "price": 54000.0,
                "compare_at_price": 60000.0,
                "stock_quantity": 60,
                "featured_image": "https://images.unsplash.com/photo-1586075010923-2dd4570fb338?auto=format&fit=crop&w=800&q=80",
                "gallery_images": [],
                "short_description": "رنگ‌های ملایم پاستلی بدون ایجاد خستگی چشم و بدون نفوذ به پشت صفحه کتاب یا جزوه.",
                "description": "<p>علامت‌گذار معروف استابیلو ساخت آلمان با فناوری ضدخشک‌شدن تا ۴ ساعت بدون درب.</p>",
                "is_featured": 1,
                "is_published": 1,
                "has_priority_system": 0,
                "priority_label_1": "",
                "priority_label_2": "",
                "priority_options": [],
                "priority_helper_text": "",
                "has_color_variants": 1,
                "color_variants": [
                    {"id": "901", "name": "هلویی ملایم", "hex": "#fed7aa", "image": "", "price": 54000.0, "sku": "STB-PCH", "stock": 20},
                    {"id": "902", "name": "نعنایی روشن", "hex": "#a7f3d0", "image": "", "price": 54000.0, "sku": "STB-MNT", "stock": 18},
                    {"id": "903", "name": "یاسی پاستلی", "hex": "#e9d5ff", "image": "", "price": 54000.0, "sku": "STB-LIL", "stock": 25}
                ],
                "meta_title": "علامت گذار پاستلی استابیلو Boss Original",
                "meta_description": "خرید هایلایتر استابیلو پاستلی با رنگ‌های جذاب نعنایی، هلویی و یاسی با ارسال سریع."
            },

            # Product 6: Priority System (Faber-Castell Eraser)
            {
                "title": "پاک‌کن فابرکاستل مدل Dust-Free فانتزی",
                "slug": "faber-castell-dust-free-eraser",
                "sku": "FBC-DF01",
                "category_id": cat_map.get("sharpeners-and-erasers"),
                "price": 22000.0,
                "compare_at_price": 26000.0,
                "stock_quantity": 90,
                "featured_image": "https://images.unsplash.com/photo-1568827999250-3f04b901594e?auto=format&fit=crop&w=800&q=80",
                "gallery_images": [],
                "short_description": "فرمولاسیون ضد براده ریز Dust-Free بدون ایجاد لکه و سیاهی روی کاغذ.",
                "description": "<p>پاک‌کن نرم و استاندارد فابرکاستل بدون فتالات و مواد مضر سمی، سازگار با محیط زیست.</p>",
                "is_featured": 0,
                "is_published": 1,
                "has_priority_system": 1,
                "priority_label_1": "اولویت رنگ بدنه ۱:",
                "priority_label_2": "اولویت رنگ بدنه ۲:",
                "priority_options": ["آبی کاربنی", "سبز فسفری", "صورتی باربی", "سفید کلاسیک"],
                "priority_helper_text": "رنگ‌های انتخابی خود را به ترتیب اولویت تعیین نمایید.",
                "has_color_variants": 0,
                "color_variants": [],
                "meta_title": "پاک کن فابرکاستل Dust-Free رنگی",
                "meta_description": "خرید پاک کن فابر کاستل بدون براده با قابلیت انتخاب اولویت رنگ بدنه."
            }
        ]

        for p in products_data:
            conn.execute(
                """
                INSERT OR IGNORE INTO products (
                    title, slug, sku, category_id, price, compare_at_price,
                    stock_quantity, is_in_stock, featured_image, gallery_images,
                    short_description, description, is_featured, is_published,
                    has_priority_system, priority_label_1, priority_label_2,
                    priority_options, priority_helper_text,
                    has_color_variants, color_variants,
                    meta_title, meta_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    p["title"], p["slug"], p["sku"], p["category_id"], p["price"], p["compare_at_price"],
                    p["stock_quantity"], p["featured_image"], json.dumps(p["gallery_images"], ensure_ascii=False),
                    p["short_description"], p["description"], p["is_featured"], p["is_published"],
                    p["has_priority_system"], p["priority_label_1"], p["priority_label_2"],
                    json.dumps(p["priority_options"], ensure_ascii=False), p["priority_helper_text"],
                    p["has_color_variants"], json.dumps(p["color_variants"], ensure_ascii=False),
                    p["meta_title"], p["meta_description"]
                )
            )

        # 3. Blog Articles
        print("[+] Seeding Blog Articles...")
        posts_data = [
            (
                "راهنمای انتخاب تراش مداد ارگونومیک برای دانش‌آموزان و طراحان",
                "ergonomic-pencil-sharpener-buying-guide",
                "بررسی انواع تیغه‌های تراش، تیغه‌های SK ژاپنی و نحوه مراقبت از نوک مدادهای گرافیتی و رنگی.",
                """
                <p>تراشیدن مداد شاید یک کار بسیار ساده به نظر برسد، اما انتخاب یک تراش غیراستاندارد می‌تواند باعث شکستن مکرر مغز مداد و هدر رفتن لوازم تحریر گران‌قیمت شما شود.</p>
                <h3>تیغه SK فولادی چیست؟</h3>
                <p>در محصولاتی نظیر پنتر Handy PS-104 از تیغه‌های فولادی با آلیاژ کربن بالا تحت استاندارد SK استفاده می‌شود. این تیغه‌ها لبه برشی بسیار دقیق دارند که چوب مداد را بدون ایجاد فشار متقارن و بدون ترک‌خوردگی می‌تراشد.</p>
                <h3>مزایای مخزن‌دار بودن تراش:</h3>
                <p>وجود مخزن شفاف علاوه بر نظافت میز تحریر و کیف مدرسه، به کودک امکان می‌دهد میزان پر شدن براده‌ها را مشاهده نموده و به موقع آن را تخلیه نماید.</p>
                """,
                "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?auto=format&fit=crop&w=800&q=80",
                "راهنمای خرید",
                "تراش, پنتر, لوازم التحریر, راهنمای خرید",
                "مهندس امینی",
                "راهنمای جامع خرید تراش ارگونومیک و استاندارد",
                "نکات مهم برای خرید تراش مناسب مدرسه و طراحی به همراه بررسی تیغه‌های فولادی ضدزنگ."
            ),
            (
                "چگونه طول عمر ماژیک وایت‌برد را تا دو برابر افزایش دهیم؟",
                "how-to-extend-whiteboard-markers-lifespan",
                "نکات ساده و موثر نگهداری از ماژیک‌های وایت‌برد اداری و آموزشی برای جلوگیری از خشک شدن جوهر.",
                """
                <p>ماژیک‌های وایت‌برد بر پایه حلال‌های الکلی فرار تولید می‌شوند. رعایت چند نکته ساده می‌تواند از خشک شدن زودهنگام آن‌ها جلوگیری کند:</p>
                <ol>
                    <li><strong>نگهداری به صورت افقی:</strong> همواره ماژیک‌ها را به صورت افقی روی جا‌ماژیکی یا میز قرار دهید تا غلظت پیگمنت جوهر در سراسر بدنه متعادل بماند.</li>
                    <li><strong>بستن سریع درب ماژیک:</strong> حتی چند دقیقه باز ماندن درب در مجاورت جریان هوا می‌تواند سطح رویی نوک نمدی را خشک کند.</li>
                    <li><strong>استفاده از تخته‌پاک‌کن مناسب:</strong> تخته‌پاک‌کن‌های کثیف جوهر را روی صفحه پخش می‌کنند و باعث می‌شوند ناچار شوید فشار بیشتری به نوک ماژیک وارد کنید.</li>
                </ol>
                """,
                "https://images.unsplash.com/photo-1585336261026-68153b6fa03d?auto=format&fit=crop&w=800&q=80",
                "نکات کاربردی",
                "ماژیک, وایت برد, نگهداری, پرشیا",
                "دکتر رضایی",
                "روش‌های نگهداری و افزایش عمر ماژیک وایت برد",
                "آموزش جلوگیری از خشک شدن ماژیک‌های وایت‌برد مدارس و ادارات."
            ),
            (
                "چک‌لیست کامل نوشت‌افزار و تجهیزات اداری برای شرکت‌های نوپا",
                "complete-office-stationery-checklist-startups",
                "فهرست ملزومات ضروری تحریر، بایگانی و کاغذ برای راه‌اندازی دفتر کار حرفه‌ای.",
                """
                <p>شروع فعالیت در یک دفتر کاری تازه نیازمند تجهیز پرسنل با ابزارهای کارآمد و استاندارد است. در این مقاله چک‌لیست اقلام اساسی تحریر را دسته‌بندی کرده‌ایم.</p>
                <h3>۱. لوازم نوشتن و ترسیم</h3>
                <p>خودکارهای اداری روان، هایلایترهای تفکیک اسناد، غلط‌گیر نواری و ماژیک‌های یادداشت پرچم‌دار.</p>
                <h3>۲. لوازم صحافی و بایگانی</h3>
                <p>منگنه رومیزی بادوام، سوزن منگنه سایز ۲۴/۶، گیره‌های دوبل و زونکن‌های عطف ۷.۵ سانتیمتری.</p>
                """,
                "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=800&q=80",
                "مدیریت اداری",
                "اداری, بایگانی, استارتاپ, خرید عمده",
                "واحد پشتیبانی",
                "چک لیست ملزومات اداری و نوشت افزار شرکت‌ها",
                "لیست جامع خرید لوازم التحریر اداری برای دفاتر شرکت‌ها با فاکتور رسمی."
            )
        ]

        for title, slug, excerpt, content, img, cat, tags, author, m_title, m_desc in posts_data:
            conn.execute(
                """
                INSERT OR IGNORE INTO blog_posts (
                    title, slug, excerpt, content, featured_image, category, tags, author_name, is_published, meta_title, meta_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (title, slug, excerpt, content, img, cat, tags, author, m_title, m_desc)
            )

        # 4. Dynamic Pages (Foundation for 100+ pages)
        print("[+] Seeding Dynamic CMS Pages (Core Foundation)...")
        pages_data = [
            (
                "قوانین و شرایط خرید و مرجوعی کالا",
                "shipping-and-returns",
                "رویه بازگشت کالا تا ۷ روز کاری و شرایط ارسال سفارشات پستی و باربری.",
                """
                <h2>شرایط و ضوابط ارسال و مرجوعی کالا</h2>
                <p>مجموعه ما در راستای جلب رضایت حداکثری مشتریان و رعایت حقوق مصرف‌کنندگان، فرآیند ارسال و مرجوعی را به شرح زیر سازماندهی نموده است:</p>
                <h3>۱. نحوه ارسال سفارشات</h3>
                <ul>
                    <li>ارسال سفارشات تهران: از طریق پیک موتوری در همان روز یا پست پیشتاز ظرف ۲۴ تا ۴۸ ساعت.</li>
                    <li>ارسال سفارشات شهرستان‌ها: از طریق پست پیشتاز، تیپاکس و شرکت‌های باربری مجاز با بسته‌بندی ایمن ضدضربه.</li>
                </ul>
                <h3>۲. ضمانت بازگشت ۷ روزه</h3>
                <p>در صورتی که کالای دریافتی دارای مغایرت فیزیکی، نقص فنی تیغه یا رنگ نامنطبق با اولویت‌های ثبت شده مشتری باشد، تا ۷ روز امکان بازگشت بی قید و شرط بدون هزینه پستی وجود دارد.</p>
                """,
                "شرایط ارسال و مرجوعی کالا | فروشگاه ما",
                "قوانین کامل ارسال، هزینه‌های حمل و نقل و گارانتی بازگشت ۷ روزه کالا."
            ),
            (
                "راهنمای ثبت سفارش عمده و خرید سازمانی",
                "bulk-orders-guide",
                "تسهیلات ویژه، تخفیف‌های پلکانی و صدور فاکتور رسمی با ارزش افزوده برای سازمان‌ها و مدارس.",
                """
                <h2>سفارشات عمده و ملزومات سازمانی</h2>
                <p>اگر مدیر مدرسه، آموزشگاه، موسسه آموزشی یا مسئول خرید شرکت هستید، می‌توانید از تخفیف‌های ویژه پلکانی ما بهره‌مند شوید.</p>
                <h3>مزایای خرید سازمانی از ما:</h3>
                <ul>
                    <li>صدور پیش‌فاکتور و فاکتور رسمی معتبر سامانه مودیان مالیاتی</li>
                    <li>امکان تعیین دقیق رنگ‌های سازمانی و اولویت‌های ارسالی</li>
                    <li>مشاوره تلفنی تخصصی جهت بهینه‌سازی هزینه‌های تحریر و نوشت‌افزار</li>
                    <li>تامین موجودی مداوم بدون نگرانی از نوسانات مقطعی بازار</li>
                </ul>
                <p>جهت ثبت درخواست پیش‌فاکتور می‌توانید از صفحه تماس با ما اقدام فرموده یا با شماره پشتیبانی تماس حاصل فرمایید.</p>
                """,
                "راهنمای خرید عمده و سازمانی نوشت افزار",
                "شرایط خرید عمده لوازم التحریر با تخفیف‌های ویژه سازمانی و فاکتور رسمی."
            ),
            (
                "پرسش‌های متداول (FAQ)",
                "faq",
                "پاسخ به سوالات پرتکرار کاربران در خصوص انتخاب اولویت، پالت رنگ و رهگیری سفارشات.",
                """
                <h2>سوالات متداول خریداران</h2>
                <h3>سیستم اولویت انتخاب چیست؟</h3>
                <p>در کالاهایی مانند تراش‌های فانتزی که دارای رنگ‌های پرطرفدار هستند، شما می‌توانید رنگ اولویت ۱ و در صورت عدم موجودی، اولویت ۲ دلخواه خود را تعیین کنید تا سفارش شما بدون تاخیر ارسال گردد.</p>
                <h3>چگونه رنگ دلخواهم را از پالت انتخاب کنم؟</h3>
                <p>در صفحه محصولاتی که دارای سیستم واریانت رنگی هستند (مانند ماژیک‌های وایت‌برد)، به سادگی بر روی دایره رنگ دلخواه کلیک کنید تا تصویر و قیمت آن به صورت خودکار بروزرسانی شود.</p>
                <h3>چقدر طول می‌کشد تا سفارش به دست من برسد؟</h3>
                <p>به طور معمول کلیه سفارشات در روز کاری پس از ثبت تحویل شرکت پست گردیده و ظرف ۲ تا ۴ روز کاری تحویل مشتری می‌گردد.</p>
                """,
                "پرسش‌های متداول خریداران (FAQ)",
                "پاسخ به متداول‌ترین سوالات درباره روند خرید، انتخاب اولویت رنگ و ارسال سفارش."
            )
        ]

        for title, slug, excerpt, body, m_title, m_desc in pages_data:
            conn.execute(
                """
                INSERT OR IGNORE INTO pages (title, slug, excerpt, body_content, template_type, is_published, meta_title, meta_description)
                VALUES (?, ?, ?, ?, 'standard', 1, ?, ?)
                """,
                (title, slug, excerpt, body, m_title, m_desc)
            )

        # 5. Menus
        print("[+] Seeding Navigation Menus...")
        conn.execute("DELETE FROM menu_items")
        header_menus = [
            ("header", "کاتالوگ محصولات", "/catalog", 1, 0),
            ("header", "تراش و پاک‌کن", "/catalog?category=sharpeners-and-erasers", 2, 0),
            ("header", "ماژیک و علامت‌گذار", "/catalog?category=markers-and-highlighters", 3, 0),
            ("header", "سفارشات عمده", "/page/bulk-orders-guide", 4, 0),
            ("header", "وبلاگ آموزشی", "/blog", 5, 0),
        ]
        for loc, lbl, url, sort_ord, new_tab in header_menus:
            conn.execute(
                "INSERT INTO menu_items (location, label, url, sort_order, is_new_tab) VALUES (?, ?, ?, ?, ?)",
                (loc, lbl, url, sort_ord, new_tab)
            )

        footer_menus = [
            ("footer", "قوانین و ارسال", "/page/shipping-and-returns", 1, 0),
            ("footer", "خرید عمده سازمان‌ها", "/page/bulk-orders-guide", 2, 0),
            ("footer", "پرسش‌های متداول", "/page/faq", 3, 0),
            ("footer", "درباره ما", "/about", 4, 0),
            ("footer", "تماس با پشتیبانی", "/contact", 5, 0),
        ]
        for loc, lbl, url, sort_ord, new_tab in footer_menus:
            conn.execute(
                "INSERT INTO menu_items (location, label, url, sort_order, is_new_tab) VALUES (?, ?, ?, ?, ?)",
                (loc, lbl, url, sort_ord, new_tab)
            )

        # 6. Sample Contact Inquiry
        print("[+] Seeding Sample Contact Inquiry...")
        conn.execute(
            """
            INSERT OR IGNORE INTO inquiries (id, full_name, email, phone, subject, message, is_read)
            VALUES (1, 'مهندس کامران رستمی', 'rostami@school.ir', '09129876543', 'استعلام خرید ۲۰۰ عدد ماژیک وایت‌برد', 'با سلام، لطفا پیش‌فاکتور رسمی برای خرید ۲۰۰ عدد ماژیک پرشیا با رنگ‌های آبی و مشکی به همراه اولویت ارسال ارسال فرمایید.', 0)
            """
        )

        # 7. Site Settings
        print("[+] Setting Global Master Options and Branding...")
        settings_defaults = {
            "brand_name": "نوشت‌افزار و تحریر مدرن",
            "tagline": "مرکز تخصصی ملزومات تحریری، تراش و ماژیک با انتخاب اولویت و رنگ",
            "logo_url": "",
            "favicon_url": "",
            "phone": "021-88997766",
            "email": "support@stationerystore.ir",
            "address": "تهران، میدان انقلاب، خیابان ۱۲ فروردین، مجتمع تحریر، پلاک ۴۲",
            "currency": "تومان",
            "default_lang": "fa",
            "rtl_mode": "1",
            "global_enable_priority": "1", # Master toggle for priority system
            "global_enable_color_variants": "1", # Master toggle for color swatches
            "footer_about": "ما با افتخار ارائه‌دهنده مرغوب‌ترین نوشت‌افزارهای استاندارد، تراش‌های ارگونومیک و ماژیک‌های وایت‌برد با نوآوری در سیستم انتخاب اولویت و پالت‌های رنگی به سراسر کشور هستیم.",
            "footer_copyright": "© ۲۰۲۶ فروشگاه نوشت‌افزار مدرن. تمامی حقوق محفوظ است."
        }
        for k, v in settings_defaults.items():
            conn.execute("INSERT OR REPLACE INTO site_settings (key, value) VALUES (?, ?)", (k, v))

    print("[SUCCESS] Database successfully seeded with rich mock data!")

if __name__ == "__main__":
    seed_database()
