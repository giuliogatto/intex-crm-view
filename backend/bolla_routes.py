"""API «Upload bolla» pagina Cicli: OCR foto DDT + matching cliente/cicli."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from bottle import HTTPResponse, request, response

from bolla_match import match_cliente, match_righe
from bolla_ocr import MAX_IMAGE_BYTES, extract_bolla, sniff_image_mime
from cicli_routes import _cicli_table_exists
from LLMservice import get_ocr_model_name

CACHE_DAYS = 30
MAX_JSON_BODY = 2 * 1024 * 1024


def _int_param(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _username() -> Optional[str]:
    user = request.environ.get("intex.user") or {}
    return user.get("username") if isinstance(user, dict) else None


def _require_user() -> None:
    # Il return dell'hook before_request è ignorato da Bottle: senza abort l'handler girerebbe comunque.
    if not request.environ.get("intex.user"):
        raise HTTPResponse(status=401, body=json.dumps({"error": "Authentication required"}),
                           headers={"Content-Type": "application/json"})


def _sessions_ready(cursor) -> bool:
    return _cicli_table_exists(cursor, "ocr_bolla_sessioni")


def _cached_ocr(cursor, sha: str, model: str) -> Optional[Dict[str, Any]]:
    cursor.execute(
        f"""
        SELECT id, ocr_json, openai_response_id
        FROM ocr_bolla_sessioni
        WHERE image_sha256 = %(sha)s AND model = %(model)s
          AND created_at >= now() - INTERVAL '{CACHE_DAYS} days'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"sha": sha, "model": model},
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {"session_id": row[0], "ocr": row[1], "response_id": row[2]}


def _match_all(cursor, ocr: Dict[str, Any], codice_cliente: Optional[str], max_cicli: int) -> Dict[str, Any]:
    cliente = match_cliente(cursor, ocr)
    scelto = codice_cliente or (cliente["selezionato"] or {}).get("codice_cliente")
    righe = (
        match_righe(cursor, scelto, ocr, max_per_riga=max_cicli)
        if scelto
        else {"codice_cliente": None, "righe_match": [], "capabilities": None}
    )
    return {
        "cliente": cliente,
        "codice_cliente": scelto,
        "righe_match": righe["righe_match"],
        "capabilities": righe["capabilities"],
    }


def register_bolla_routes(app, db_pool):
    """Registra /api/cicli/ocr-bolla* sull'app Bottle."""

    @app.route("/api/cicli/ocr-bolla", method="POST")
    def ocr_bolla():
        _require_user()
        upload = request.files.get("file")
        if upload is None:
            response.status = 400
            return {"error": "Nessun file: inviare l'immagine nel campo multipart 'file'."}

        image = upload.file.read(MAX_IMAGE_BYTES + 1)
        if len(image) > MAX_IMAGE_BYTES:
            response.status = 413
            return {"error": f"Immagine troppo grande (max {MAX_IMAGE_BYTES // (1024 * 1024)} MB)."}
        mime = sniff_image_mime(image)
        if not mime:
            response.status = 415
            return {"error": "Formato non supportato: caricare JPEG, PNG o WEBP."}

        codice_cliente = (request.forms.get("codice_cliente") or "").strip() or None
        force = (request.forms.get("force") or "").strip() in ("1", "true")
        max_cicli = _int_param(request.forms.get("max_cicli_per_riga"), 5, 1, 20)
        sha = hashlib.sha256(image).hexdigest()
        model = get_ocr_model_name()

        cached = None
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            sessions_ok = _sessions_ready(cursor)
            if sessions_ok and not force:
                cached = _cached_ocr(cursor, sha, model)
            cursor.close()
        finally:
            db_pool.release_conn(conn)

        if cached:
            ocr, response_id = cached["ocr"], cached["response_id"]
        else:
            try:
                extracted = extract_bolla(image, mime)
            except ValueError as e:
                response.status = 503
                return {"error": str(e)}
            except Exception as e:
                response.status = 502
                return {"error": f"Errore OCR: {e}"}
            ocr, response_id = extracted["ocr"], extracted["response_id"]

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            result = _match_all(cursor, ocr, codice_cliente, max_cicli)
            session_id = cached["session_id"] if cached else None
            if sessions_ok:
                match_json = json.dumps({k: result[k] for k in ("cliente", "righe_match")})
                if session_id:
                    cursor.execute(
                        """
                        UPDATE ocr_bolla_sessioni
                        SET cliente_scelto = %(cli)s, match_json = %(match)s::jsonb, updated_at = now()
                        WHERE id = %(id)s
                        """,
                        {"cli": result["codice_cliente"], "match": match_json, "id": session_id},
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO ocr_bolla_sessioni (
                          username, image_sha256, mime_type, image_bytes, model,
                          openai_response_id, ocr_json, cliente_scelto, match_json
                        ) VALUES (
                          %(user)s, %(sha)s, %(mime)s, %(size)s, %(model)s,
                          %(rid)s, %(ocr)s::jsonb, %(cli)s, %(match)s::jsonb
                        ) RETURNING id
                        """,
                        {
                            "user": _username(),
                            "sha": sha,
                            "mime": mime,
                            "size": len(image),
                            "model": model,
                            "rid": response_id,
                            "ocr": json.dumps(ocr),
                            "cli": result["codice_cliente"],
                            "match": match_json,
                        },
                    )
                    session_id = cursor.fetchone()[0]
                conn.commit()
            cursor.close()
        except Exception as e:
            conn.rollback()
            response.status = 500
            return {"error": f"Errore matching: {e}", "ocr": ocr}
        finally:
            db_pool.release_conn(conn)

        return {
            "session_id": session_id,
            "cached": bool(cached),
            "model": model,
            "ocr": ocr,
            **result,
        }

    @app.route("/api/cicli/ocr-bolla/match", method="POST")
    def ocr_bolla_match():
        """Ricalcola il matching (es. cliente cambiato) senza ripetere l'OCR."""
        _require_user()
        if (request.content_length or 0) > MAX_JSON_BODY:
            response.status = 413
            return {"error": "Body troppo grande"}
        try:
            body = json.loads(request.body.read(MAX_JSON_BODY) or b"{}")
        except ValueError:
            response.status = 400
            return {"error": "JSON non valido"}

        session_id = body.get("session_id")
        ocr = body.get("ocr")
        codice_cliente = (body.get("codice_cliente") or "").strip() or None
        max_cicli = _int_param(body.get("max_cicli_per_riga"), 5, 1, 20)

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            sessions_ok = _sessions_ready(cursor)
            if ocr is None and session_id and sessions_ok:
                cursor.execute("SELECT ocr_json FROM ocr_bolla_sessioni WHERE id = %(id)s", {"id": session_id})
                row = cursor.fetchone()
                ocr = row[0] if row else None
            if not isinstance(ocr, dict):
                cursor.close()
                response.status = 400
                return {"error": "Fornire 'ocr' o un 'session_id' valido."}

            result = _match_all(cursor, ocr, codice_cliente, max_cicli)
            if session_id and sessions_ok:
                cursor.execute(
                    """
                    UPDATE ocr_bolla_sessioni
                    SET cliente_scelto = %(cli)s, match_json = %(match)s::jsonb, updated_at = now()
                    WHERE id = %(id)s
                    """,
                    {
                        "cli": result["codice_cliente"],
                        "match": json.dumps({k: result[k] for k in ("cliente", "righe_match")}),
                        "id": session_id,
                    },
                )
                conn.commit()
            cursor.close()
        except Exception as e:
            conn.rollback()
            response.status = 500
            return {"error": f"Errore matching: {e}"}
        finally:
            db_pool.release_conn(conn)

        return {"session_id": session_id, "ocr": ocr, **result}
