import os
import hmac
import hashlib
import base64
import json
import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from app.config import settings
from app.database import get_db

SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hashes a password with PBKDF2 HMAC SHA-256 and returns (hash, salt)."""
    if salt is None:
        salt = base64.b64encode(os.urandom(16)).decode('utf-8')
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100_000
    )
    pw_hash = base64.b64encode(key).decode('utf-8')
    return pw_hash, salt

def verify_password(plain_password: str, pw_hash: str, salt: str) -> bool:
    """Verifies a plain password against the stored hash and salt."""
    expected_hash, _ = hash_password(plain_password, salt)
    return hmac.compare_digest(expected_hash, pw_hash)

def create_session_token(data: dict) -> str:
    """Creates a signed session token containing user payload and expiration."""
    payload = data.copy()
    payload["exp"] = int(time.time()) + SESSION_MAX_AGE
    payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode('utf-8')

    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode('utf-8')

    return f"{payload_b64}.{sig_b64}"

def decode_session_token(token: str) -> Optional[dict]:
    """Validates and decodes a session token."""
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        payload_b64, sig_b64 = parts

        expected_sig = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).digest()
        provided_sig = base64.urlsafe_b64decode(sig_b64.encode('utf-8'))

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_json = base64.urlsafe_b64decode(payload_b64.encode('utf-8')).decode('utf-8')
        payload = json.loads(payload_json)

        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None

def get_current_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """Extracts user from the session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    session_data = decode_session_token(token)
    if not session_data or "user_id" not in session_data:
        return None

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, full_name, role, is_active FROM users WHERE id = ?",
            (session_data["user_id"],)
        ).fetchone()
        if not row or not row["is_active"]:
            return None
        return dict(row)

def require_auth(request: Request) -> Dict[str, Any]:
    """Dependency for routes that require any logged-in user."""
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"}
        )
    return user

def require_admin(request: Request) -> Dict[str, Any]:
    """Dependency for routes that require an 'admin' role."""
    user = require_auth(request)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required"
        )
    return user
