import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "production")
    DEBUG: bool = APP_ENV.lower() == "development"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    SITE_URL: str = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "prod-secret-key-antigravity-secure-seed-983141")
    
    # Support serverless read-write environments (Vercel / Lambda)
    _default_db = BASE_DIR / os.getenv("DATABASE_PATH", "app.db")
    if os.getenv("VERCEL") and Path("/tmp").exists():
        import shutil
        _tmp_db = Path("/tmp/app.db")
        if not _tmp_db.exists() and _default_db.exists():
            shutil.copy2(_default_db, _tmp_db)
        DATABASE_PATH: str = str(_tmp_db)
    else:
        DATABASE_PATH: str = str(_default_db)

    FORCE_HTTPS: bool = os.getenv("FORCE_HTTPS", "false").lower() in ("true", "1", "yes")

    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123456")
    ADMIN_NAME: str = os.getenv("ADMIN_NAME", "Site Administrator")

    UPLOAD_DIR: Path = BASE_DIR / "app" / "static" / "uploads"

settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
