@echo off
setlocal
chcp 65001 >nul
title Modern E-Commerce and Business CMS Platform - Optimized Multi-Worker

echo ======================================================================
echo    Modern Business and E-Commerce CMS Platform
echo    سامانه پیشرفته فروشگاهی و مدیریت محتوا با قابلیت پردازش چندورکری
echo ======================================================================
echo.

set "PY_BIN="

if exist "%LOCALAPPDATA%\Python\bin\python.exe" set "PY_BIN=%LOCALAPPDATA%\Python\bin\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" set "PY_BIN=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY_BIN if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if not defined PY_BIN (
    py -3 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY_BIN=py -3"
)

if not defined PY_BIN (
    python -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY_BIN=python"
)

if not defined PY_BIN (
    echo [ERROR] مفسر پایتون معتبر بر روی سیستم شما شناسایی نشد.
    echo لطفاً Python نسخه 3.10 به بالا را نصب کنید یا متغیر PATH را تنظیم نمایید.
    pause
    exit /b 1
)

echo [OK] پایتون شناسایی شد: %PY_BIN%
echo [OK] در حال اجرای سرور چندورکری با کارایی حداکثری...
echo.
echo آدرس فروشگاه:             http://localhost:8000
echo پنل مدیریت:               http://localhost:8000/admin
echo ایمیل ورود مدیر:          admin@example.com
echo رمز عبور مدیر:           admin123456
echo مستندات خودکار API:      http://localhost:8000/docs
echo ======================================================================
echo.

start "" "http://localhost:8000"
"%PY_BIN%" run.py --workers 4

pause
