import os
import sys
import argparse
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings
from seed import seed_database
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Modern Business & E-Commerce CMS Runner")
    parser.add_argument("--workers", type=int, default=None, help="Number of worker processes")
    parser.add_argument("--host", type=str, default=None, help="Host to bind to")
    parser.add_argument("--port", type=int, default=None, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable autoreload (single worker development mode)")
    args = parser.parse_args()

    cpu_cores = os.cpu_count() or 1
    default_workers = min(cpu_cores, 8)

    # Resolve configuration
    host = args.host or settings.HOST
    port = args.port or settings.PORT

    # Worker count logic: user CLI > env var > default CPU cores
    if args.workers is not None:
        workers = args.workers
    elif os.getenv("WORKERS"):
        workers = int(os.getenv("WORKERS"))
    else:
        workers = default_workers

    # If reload is explicitly requested or DEBUG is true without workers specified
    enable_reload = args.reload or (settings.DEBUG and args.workers is None and not os.getenv("WORKERS"))
    if enable_reload:
        workers = 1

    print("=" * 65)
    print(">> Modern Business & E-Commerce CMS Platform (High Performance)")
    print(f">> Environment:     {settings.APP_ENV.upper()}")
    print(f">> Host & Port:     {host}:{port}")
    print(f">> CPU Cores:       {cpu_cores}")
    print(f">> Worker Count:    {workers} Worker Process(es)")
    print(f">> Reload Mode:     {'ENABLED (Single-Worker)' if enable_reload else 'DISABLED (High-Concurrency Multi-Worker)'}")
    print(f">> SSL / HTTPS:     {'FORCED' if settings.FORCE_HTTPS else 'STANDARD'}")
    print("=" * 65)

    # Automatically seed database if database file doesn't exist yet
    db_file = Path(settings.DATABASE_PATH)
    if not db_file.exists():
        print("[*] Database not found. Seeding initial data now...")
        seed_database()
    else:
        print("[*] Existing database detected at:", settings.DATABASE_PATH)

    print(f"\n[+] Storefront URL:      http://localhost:{port}")
    print(f"[+] Admin Dashboard:     http://localhost:{port}/admin")
    print(f"    Admin Email:         {settings.ADMIN_EMAIL}")
    print(f"    Admin Password:      {settings.ADMIN_PASSWORD}")
    print(f"[+] API Documentation:   http://localhost:{port}/docs\n")

    if enable_reload:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True
        )
    else:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            workers=workers,
            http="httptools",
            loop="asyncio",
            access_log=True,
            timeout_keep_alive=30
        )

if __name__ == "__main__":
    main()
