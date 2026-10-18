"""API amministrazione: sinonimi ricerca, storico OCR bolle, logs di accesso."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from bottle import HTTPResponse, request, response

from bolla_routes import resolve_bolla_image
from cicli_routes import _cicli_table_exists


_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": (
        "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, Authorization"
    ),
}


def _json_error(status: int, message: str) -> HTTPResponse:
    return HTTPResponse(
        status=status,
        body=json.dumps({"error": message}),
        headers={"Content-Type": "application/json", **_CORS},
    )


def _require_admin() -> Tuple[Optional[Dict[str, Any]], Optional[HTTPResponse]]:
    user = request.environ.get("intex.user") or {}
    if not isinstance(user, dict) or user.get("role") != "admin":
        return None, _json_error(403, "Admin access required")
    return user, None


def _int_param(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _normalize_termine(value: Any) -> str:
    return " ".join(str(value or "").strip().upper().split())


def _as_json_obj(value: Any) -> Any:
    """psycopg2 a volte restituisce jsonb già come dict, a volte come str."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, memoryview)):
        value = bytes(value).decode("utf-8")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return None
    return value


def register_admin_routes(app, db_pool):
    """Registra /api/admin/* sull'app Bottle."""

    # ------------------------------------------------------------------
    # Sinonimi ricerca (ricerca_sinonimi)
    # ------------------------------------------------------------------

    @app.route("/api/admin/sinonimi", method="GET")
    def list_sinonimi():
        denied = _require_admin()
        if denied[0] is None:
            raise denied[1]

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            if not _cicli_table_exists(cursor, "ricerca_sinonimi"):
                cursor.close()
                response.status = 503
                return {"error": "Tabella ricerca_sinonimi non presente. Applicare le migration."}

            cursor.execute(
                """
                SELECT gruppo, termine
                FROM ricerca_sinonimi
                ORDER BY gruppo ASC, termine ASC
                """
            )
            rows = cursor.fetchall()
            cursor.close()
            data = [{"gruppo": r[0], "termine": r[1]} for r in rows]
            gruppi = sorted({item["gruppo"] for item in data})
            return {"data": data, "gruppi": gruppi, "total": len(data)}
        except Exception as e:
            response.status = 500
            return {"error": str(e)}
        finally:
            db_pool.release_conn(conn)

    @app.route("/api/admin/sinonimi", method="POST")
    def create_sinonimo():
        denied = _require_admin()
        if denied[0] is None:
            raise denied[1]

        body = request.json or {}
        gruppo = _normalize_termine(body.get("gruppo"))
        termine = _normalize_termine(body.get("termine"))
        if not gruppo or not termine:
            response.status = 400
            return {"error": "gruppo e termine sono obbligatori"}
        if len(gruppo) > 50 or len(termine) > 50:
            response.status = 400
            return {"error": "gruppo e termine max 50 caratteri"}

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            if not _cicli_table_exists(cursor, "ricerca_sinonimi"):
                cursor.close()
                response.status = 503
                return {"error": "Tabella ricerca_sinonimi non presente."}

            cursor.execute(
                """
                INSERT INTO ricerca_sinonimi (gruppo, termine)
                VALUES (%(gruppo)s, %(termine)s)
                ON CONFLICT DO NOTHING
                RETURNING gruppo, termine
                """,
                {"gruppo": gruppo, "termine": termine},
            )
            row = cursor.fetchone()
            conn.commit()
            cursor.close()
            if not row:
                response.status = 409
                return {"error": "Sinonimo già presente"}
            return {"gruppo": row[0], "termine": row[1]}
        except Exception as e:
            conn.rollback()
            response.status = 500
            return {"error": str(e)}
        finally:
            db_pool.release_conn(conn)

    @app.route("/api/admin/sinonimi", method="DELETE")
    def delete_sinonimo():
        denied = _require_admin()
        if denied[0] is None:
            raise denied[1]

        body = request.json or {}
        gruppo = _normalize_termine(body.get("gruppo") or request.query.get("gruppo"))
        termine = _normalize_termine(body.get("termine") or request.query.get("termine"))
        if not gruppo or not termine:
            response.status = 400
            return {"error": "gruppo e termine sono obbligatori"}

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM ricerca_sinonimi
                WHERE gruppo = %(gruppo)s AND termine = %(termine)s
                """,
                {"gruppo": gruppo, "termine": termine},
            )
            deleted = cursor.rowcount
            conn.commit()
            cursor.close()
            if deleted == 0:
                response.status = 404
                return {"error": "Sinonimo non trovato"}
            return {"ok": True, "deleted": deleted}
        except Exception as e:
            conn.rollback()
            response.status = 500
            return {"error": str(e)}
        finally:
            db_pool.release_conn(conn)

    # ------------------------------------------------------------------
    # Storico OCR bolle
    # ------------------------------------------------------------------

    @app.route("/api/admin/ocr-bolle", method="GET")
    def list_ocr_bolle():
        denied = _require_admin()
        if denied[0] is None:
            raise denied[1]

        page = _int_param(request.query.get("page"), 1, 1, 1_000_000)
        limit = _int_param(request.query.get("limit"), 20, 1, 100)
        offset = (page - 1) * limit
        q = (request.query.get("q") or "").strip()

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            if not _cicli_table_exists(cursor, "ocr_bolla_sessioni"):
                cursor.close()
                response.status = 503
                return {"error": "Tabella ocr_bolla_sessioni non presente. Applicare le migration."}

            where = "TRUE"
            params: Dict[str, Any] = {"limit": limit, "offset": offset}
            if q:
                where = (
                    "(username ILIKE %(q)s OR cliente_scelto ILIKE %(q)s "
                    "OR image_sha256 ILIKE %(q)s OR CAST(id AS TEXT) = %(qid)s)"
                )
                params["q"] = f"%{q}%"
                params["qid"] = q

            cursor.execute(
                f"SELECT COUNT(*) FROM ocr_bolla_sessioni WHERE {where}",
                params,
            )
            total = cursor.fetchone()[0]

            cursor.execute(
                f"""
                SELECT id, username, image_sha256, mime_type, image_bytes, image_path,
                       model, cliente_scelto,
                       TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI:SS') AS created_at,
                       jsonb_array_length(COALESCE(ocr_json->'righe', '[]'::jsonb)) AS n_righe,
                       (image_path IS NOT NULL AND image_path <> '') AS has_image_path
                FROM ocr_bolla_sessioni
                WHERE {where}
                ORDER BY created_at DESC, id DESC
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                params,
            )
            rows = cursor.fetchall()
            cursor.close()

            data = []
            for r in rows:
                rel = r[5]
                data.append(
                    {
                        "id": r[0],
                        "username": r[1],
                        "image_sha256": r[2],
                        "mime_type": r[3],
                        "image_bytes": r[4],
                        "image_path": rel,
                        "model": r[6],
                        "cliente_scelto": r[7],
                        "created_at": r[8],
                        "n_righe": r[9] or 0,
                        "has_image": bool(resolve_bolla_image(rel)),
                    }
                )

            pages = max((total + limit - 1) // limit, 1) if total else 1
            return {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "data": data,
            }
        except Exception as e:
            response.status = 500
            return {"error": str(e)}
        finally:
            db_pool.release_conn(conn)

    @app.route("/api/admin/ocr-bolle/<session_id:int>", method="GET")
    def get_ocr_bolla(session_id):
        denied = _require_admin()
        if denied[0] is None:
            raise denied[1]

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, image_sha256, mime_type, image_bytes, image_path,
                       model, openai_response_id, ocr_json, cliente_scelto, match_json,
                       TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI:SS') AS created_at,
                       TO_CHAR(updated_at, 'DD/MM/YYYY HH24:MI:SS') AS updated_at
                FROM ocr_bolla_sessioni
                WHERE id = %(id)s
                """,
                {"id": session_id},
            )
            row = cursor.fetchone()
            cursor.close()
            if not row:
                response.status = 404
                return {"error": "Sessione non trovata"}

            rel = row[5]
            ocr = _as_json_obj(row[8])
            match = _as_json_obj(row[10])
            if not isinstance(ocr, dict):
                ocr = {}
            if not isinstance(match, dict):
                match = {}
            righe_match = match.get("righe_match") if isinstance(match.get("righe_match"), list) else []
            return {
                "id": row[0],
                "username": row[1],
                "image_sha256": row[2],
                "mime_type": row[3],
                "image_bytes": row[4],
                "image_path": rel,
                "model": row[6],
                "openai_response_id": row[7],
                "ocr": ocr,
                "cliente_scelto": row[9],
                "match": match,
                "created_at": row[11],
                "updated_at": row[12],
                "has_image": bool(resolve_bolla_image(rel)),
                "n_righe_ocr": len(ocr.get("righe") or []),
                "n_righe_match": len(righe_match),
            }
        except Exception as e:
            response.status = 500
            return {"error": str(e)}
        finally:
            db_pool.release_conn(conn)

    @app.route("/api/admin/ocr-bolle/<session_id:int>/image", method="GET")
    def get_ocr_bolla_image(session_id):
        denied = _require_admin()
        if denied[0] is None:
            raise denied[1]

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT image_path, mime_type
                FROM ocr_bolla_sessioni
                WHERE id = %(id)s
                """,
                {"id": session_id},
            )
            row = cursor.fetchone()
            cursor.close()
        except Exception as e:
            response.status = 500
            return {"error": str(e)}
        finally:
            db_pool.release_conn(conn)

        if not row:
            raise _json_error(404, "Sessione non trovata")

        path = resolve_bolla_image(row[0])
        if not path:
            raise _json_error(404, "Immagine non disponibile su disco")

        mime = row[1] or "application/octet-stream"
        data = path.read_bytes()
        return HTTPResponse(
            body=data,
            status=200,
            headers={
                "Content-Type": mime,
                "Content-Length": str(len(data)),
                "Cache-Control": "private, max-age=3600",
                **_CORS,
            },
        )

    # ------------------------------------------------------------------
    # Logs di accesso (login + ricerche)
    # ------------------------------------------------------------------

    @app.route("/api/admin/logs", method="GET")
    def list_logs():
        denied = _require_admin()
        if denied[0] is None:
            raise denied[1]

        page = _int_param(request.query.get("page"), 1, 1, 1_000_000)
        limit = _int_param(request.query.get("limit"), 100, 1, 100)
        offset = (page - 1) * limit
        q = (request.query.get("q") or "").strip()
        event_type = (request.query.get("event_type") or "").strip().lower()
        if event_type and event_type not in ("login", "search"):
            raise _json_error(400, "event_type deve essere login o search")

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            if not _cicli_table_exists(cursor, "logs"):
                cursor.close()
                response.status = 503
                return {"error": "Tabella logs non presente. Applicare la migration create-logs.sql."}

            clauses = ["TRUE"]
            params: Dict[str, Any] = {"limit": limit, "offset": offset}
            if event_type:
                clauses.append("event_type = %(event_type)s")
                params["event_type"] = event_type
            if q:
                clauses.append(
                    "("
                    "username ILIKE %(q)s "
                    "OR ip ILIKE %(q)s "
                    "OR CAST(details AS TEXT) ILIKE %(q)s "
                    "OR CAST(id AS TEXT) = %(qid)s"
                    ")"
                )
                params["q"] = f"%{q}%"
                params["qid"] = q

            where = " AND ".join(clauses)

            cursor.execute(f"SELECT COUNT(*) FROM logs WHERE {where}", params)
            total = cursor.fetchone()[0]

            cursor.execute(
                f"""
                SELECT id, event_type, user_id, username, details, ip, user_agent,
                       TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI:SS') AS created_at_fmt
                FROM logs
                WHERE {where}
                ORDER BY created_at DESC, id DESC
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                params,
            )
            rows = cursor.fetchall()
            cursor.close()

            data = [
                {
                    "id": r[0],
                    "event_type": r[1],
                    "user_id": r[2],
                    "username": r[3],
                    "details": _as_json_obj(r[4]) or {},
                    "ip": r[5],
                    "user_agent": r[6],
                    "created_at": r[7],
                }
                for r in rows
            ]

            pages = max((total + limit - 1) // limit, 1) if total else 1
            return {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "data": data,
            }
        except Exception as e:
            response.status = 500
            return {"error": str(e)}
        finally:
            db_pool.release_conn(conn)
