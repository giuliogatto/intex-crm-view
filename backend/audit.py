"""Scrittura audit su tabella logs. Non deve mai far fallire la richiesta principale."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from bottle import request

logger = logging.getLogger(__name__)

EVENT_LOGIN = "login"
EVENT_SEARCH = "search"


def _client_ip() -> Optional[str]:
    forwarded = (request.get_header("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded:
        return forwarded[:64]
    try:
        return (request.remote_addr or "")[:64] or None
    except Exception:
        return None


def _user_agent() -> Optional[str]:
    ua = request.get_header("User-Agent")
    return ua if ua else None


def write_log(
    db_pool,
    event_type: str,
    *,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    conn = None
    cursor = None
    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO logs (event_type, user_id, username, details, ip, user_agent)
            VALUES (
              %(event_type)s,
              %(user_id)s,
              %(username)s,
              %(details)s::jsonb,
              %(ip)s,
              %(user_agent)s
            )
            """,
            {
                "event_type": event_type,
                "user_id": user_id,
                "username": username,
                "details": json.dumps(details or {}, default=str),
                "ip": _client_ip(),
                "user_agent": _user_agent(),
            },
        )
        conn.commit()
    except Exception:
        logger.exception("Failed to write audit log event_type=%s", event_type)
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                db_pool.release_conn(conn)
            except Exception:
                pass


def log_login(
    db_pool,
    *,
    user_id: Optional[int],
    username: str,
    success: bool,
    role: Optional[str] = None,
) -> None:
    details: Dict[str, Any] = {"success": success}
    if role is not None:
        details["role"] = role
    write_log(
        db_pool,
        EVENT_LOGIN,
        user_id=user_id,
        username=username,
        details=details,
    )


def log_search(
    db_pool,
    *,
    user_id: Optional[int],
    username: Optional[str],
    filters: Dict[str, Any],
    page: int,
    limit: int,
    result_total: Optional[int] = None,
    endpoint: str = "/api/cicli",
) -> None:
    # Solo filtri valorizzati, per tenere i log leggibili
    cleaned = {k: v for k, v in (filters or {}).items() if v not in (None, "", [], False)}
    details: Dict[str, Any] = {
        "endpoint": endpoint,
        "filters": cleaned,
        "page": page,
        "limit": limit,
    }
    if result_total is not None:
        details["result_total"] = result_total
    write_log(
        db_pool,
        EVENT_SEARCH,
        user_id=user_id,
        username=username,
        details=details,
    )
