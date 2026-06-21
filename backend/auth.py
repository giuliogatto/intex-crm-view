import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from bottle import request

PBKDF2_ITERATIONS = 100_000
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def _auth_secret():
    return os.getenv("AUTH_SECRET", "intex-dev-auth-secret-change-me")


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"{salt}${digest.hex()}"


def verify_password(password, stored_hash):
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, expected = stored_hash.split("$", 1)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return secrets.compare_digest(digest.hex(), expected)


def create_token(user_id, username, role):
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    data = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    signature = hmac.new(
        _auth_secret().encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{data}.{signature}"


def decode_token(token):
    if not token or "." not in token:
        return None

    data, signature = token.rsplit(".", 1)
    expected = hmac.new(
        _auth_secret().encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        payload = json.loads(base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None

    if payload.get("exp", 0) < time.time():
        return None
    return payload


def get_bearer_token():
    auth_header = request.get_header("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


def authenticate_user(db_pool, username, password):
    conn = db_pool.get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, username, password_hash, role, is_active
            FROM users
            WHERE username = %(username)s
            """,
            {"username": username},
        )
        row = cursor.fetchone()
        if not row:
            return None
        user_id, db_username, password_hash, role, is_active = row
        if not is_active or not verify_password(password, password_hash):
            return None
        return {
            "id": user_id,
            "username": db_username,
            "role": role,
        }
    finally:
        cursor.close()
        db_pool.release_conn(conn)


def get_current_user(db_pool):
    token = get_bearer_token()
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    conn = db_pool.get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, username, role, is_active
            FROM users
            WHERE id = %(user_id)s
            """,
            {"user_id": payload["sub"]},
        )
        row = cursor.fetchone()
        if not row:
            return None
        user_id, username, role, is_active = row
        if not is_active:
            return None
        return {
            "id": user_id,
            "username": username,
            "role": role,
        }
    finally:
        cursor.close()
        db_pool.release_conn(conn)
