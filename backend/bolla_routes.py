"""API «Upload bolla» pagina Cicli: OCR foto DDT + matching cliente/cicli."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from bottle import HTTPResponse, MultipartError, request, response

from bolla_match import match_cliente, match_righe
from bolla_ocr import (
    MAX_IMAGE_BYTES,
    extract_bolla_images,
    is_pdf_mime,
    prepare_bolla_images,
    sniff_image_mime,
)
from cicli_routes import _cicli_table_exists
from LLMservice import get_ocr_model_name


def _log(msg: str) -> None:
    print(f"[ocr-bolla] {msg}", file=sys.stderr, flush=True)

CACHE_DAYS = 30
MAX_JSON_BODY = 2 * 1024 * 1024

_MIME_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}

_ACCEPTED_FORMAT_MSG = "Formato non supportato: caricare JPEG, PNG, WEBP o PDF."

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": (
        "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, Authorization"
    ),
}


def images_dir() -> Path:
    """Directory persistente per le foto bolle (volume Docker in produzione)."""
    configured = (os.getenv("OCR_BOLLA_IMAGES_DIR") or "").strip()
    if configured:
        path = Path(configured)
    else:
        path = Path(__file__).resolve().parent / "var" / "ocr-bolla-images"
    path.mkdir(parents=True, exist_ok=True)
    return path


def persist_bolla_image(sha: str, mime: str, image: bytes) -> str:
    """Salva l'immagine su disco (idempotente per sha). Ritorna path relativo."""
    ext = _MIME_EXT.get(mime or "", ".bin")
    rel = f"{sha}{ext}"
    dest = images_dir() / rel
    if not dest.exists():
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(image)
        tmp.replace(dest)
        _log(f"image saved {rel} ({len(image)} bytes)")
    return rel


def resolve_bolla_image(rel_path: Optional[str]) -> Optional[Path]:
    if not rel_path:
        return None
    # Solo basename: evita path traversal
    name = Path(rel_path).name
    if name != rel_path or ".." in rel_path:
        return None
    path = images_dir() / name
    return path if path.is_file() else None


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
        raise HTTPResponse(
            status=401,
            body=json.dumps({"error": "Authentication required"}),
            headers={"Content-Type": "application/json", **_CORS_HEADERS},
        )


def _read_upload() -> Tuple[Any, Optional[bytes]]:
    """Legge il file multipart; gestisce MultipartError (MEMFILE) e assenza file."""
    try:
        upload = request.files.get("file")
    except MultipartError as e:
        raise HTTPResponse(
            status=413,
            body=json.dumps({
                "error": (
                    "Upload troppo grande o multipart non valido. "
                    f"Dettaglio: {e}"
                )
            }),
            headers={"Content-Type": "application/json", **_CORS_HEADERS},
        )
    if upload is None:
        return None, None
    image = upload.file.read(MAX_IMAGE_BYTES + 1)
    return upload, image


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

    @app.route("/api/cicli/ocr-bolla/diag", method="GET")
    def ocr_bolla_diag():
        """Diagnostica OCR: chiave presente + reachability OpenAI (senza spendere token vision)."""
        _require_user()
        import requests as req

        key = os.getenv("OPENAI_APIKEY") or ""
        try:
            import pypdfium2  # noqa: F401
            pdf_ok = True
        except ImportError:
            pdf_ok = False
        out: Dict[str, Any] = {
            "openai_key_present": bool(key),
            "openai_key_prefix": (key[:7] + "…") if key else None,
            "ocr_model": get_ocr_model_name(),
            "ocr_detail": os.getenv("OPENAI_OCR_DETAIL") or "original",
            "memfile_max": int(__import__("bottle").BaseRequest.MEMFILE_MAX),
            "pdf_support": pdf_ok,
            "accepted_formats": ["image/jpeg", "image/png", "image/webp", "application/pdf"],
        }
        try:
            r = req.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"} if key else {},
                timeout=(5, 15),
            )
            out["openai_reachable"] = True
            out["openai_models_status"] = r.status_code
        except Exception as e:
            out["openai_reachable"] = False
            out["openai_error"] = f"{type(e).__name__}: {e}"
        return out

    @app.route("/api/cicli/ocr-bolla", method="POST")
    def ocr_bolla():
        _require_user()
        _log(f"POST start user={_username()!r}")
        upload, image = _read_upload()
        if upload is None or image is None:
            response.status = 400
            return {"error": "Nessun file: inviare l'immagine nel campo multipart 'file'."}

        if len(image) > MAX_IMAGE_BYTES:
            response.status = 413
            return {
                "error": (
                    f"File troppo grande (max {MAX_IMAGE_BYTES // (1024 * 1024)} MB)."
                )
            }
        mime = sniff_image_mime(image)
        if not mime:
            response.status = 415
            return {"error": _ACCEPTED_FORMAT_MSG}

        try:
            prepared = prepare_bolla_images(image, mime)
        except ValueError as e:
            _log(f"prepare ValueError: {e}")
            response.status = 400
            return {"error": str(e)}
        except RuntimeError as e:
            _log(f"prepare RuntimeError: {e}")
            response.status = 503
            return {"error": str(e)}

        persist_bytes = prepared["persist_bytes"]
        persist_mime = prepared["persist_mime"]
        source_mime = prepared["source_mime"]
        ocr_images = prepared["ocr_images"]

        codice_cliente = (request.forms.get("codice_cliente") or "").strip() or None
        force = (request.forms.get("force") or "").strip() in ("1", "true")
        max_cicli = _int_param(request.forms.get("max_cicli_per_riga"), 5, 1, 20)
        # Cache sulla firma del file originale (PDF incluso), non sulla JPEG rasterizzata.
        sha = hashlib.sha256(image).hexdigest()
        model = get_ocr_model_name()
        pages_info = ""
        if is_pdf_mime(source_mime):
            pages_info = (
                f" pdf_pages={prepared['pdf_pages_used']}/{prepared['pdf_pages_total']}"
            )
        _log(
            f"file ok mime={source_mime} bytes={len(image)} sha={sha[:12]} "
            f"model={model} force={force}{pages_info}"
        )

        if not (os.getenv("OPENAI_APIKEY") or ""):
            _log("OPENAI_APIKEY mancante nell'ambiente del container")
            response.status = 503
            return {"error": "OPENAI_APIKEY non configurata sul server."}

        cached = None
        sessions_ok = False
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            sessions_ok = _sessions_ready(cursor)
            _log(f"sessions_table={'yes' if sessions_ok else 'no'}")
            if sessions_ok and not force:
                cached = _cached_ocr(cursor, sha, model)
            cursor.close()
        finally:
            db_pool.release_conn(conn)

        if cached:
            _log(f"cache hit session_id={cached['session_id']}")
            ocr, response_id = cached["ocr"], cached["response_id"]
        else:
            _log(f"cache miss → chiamo OpenAI Vision ({len(ocr_images)} img)")
            try:
                extracted = extract_bolla_images(
                    ocr_images,
                    extra_warnings=prepared.get("warnings"),
                )
            except ValueError as e:
                _log(f"OCR ValueError: {e}")
                response.status = 503
                return {"error": str(e)}
            except Exception as e:
                _log(f"OCR Exception: {e}")
                traceback.print_exc(file=sys.stderr)
                msg = str(e)
                if msg.startswith("OCR_NO_CREDITS:"):
                    response.status = 402
                    return {
                        "error": msg.split(":", 1)[1].strip(),
                        "code": "ocr_no_credits",
                    }
                if msg.startswith("OCR_RATE_LIMIT:"):
                    response.status = 429
                    return {
                        "error": msg.split(":", 1)[1].strip(),
                        "code": "ocr_rate_limit",
                    }
                if "timeout" in msg.lower() or "connessione" in msg.lower():
                    response.status = 504
                    return {"error": msg}
                response.status = 502
                return {"error": f"Errore OCR: {e}"}
            ocr, response_id = extracted["ocr"], extracted["response_id"]
            _log(f"OCR ok response_id={response_id} righe={len(ocr.get('righe') or [])}")

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            if not sessions_ok:
                sessions_ok = _sessions_ready(cursor)
            _log("matching…")
            result = _match_all(cursor, ocr, codice_cliente, max_cicli)
            session_id = cached["session_id"] if cached else None
            image_path = None
            try:
                # Anteprima sempre come immagine (per PDF: prima pagina rasterizzata).
                image_path = persist_bolla_image(sha, persist_mime, persist_bytes)
            except OSError as e:
                _log(f"image persist failed: {e}")
            if sessions_ok:
                match_json = json.dumps({
                    k: result[k] for k in ("cliente", "righe_match", "capabilities")
                })
                if session_id:
                    cursor.execute(
                        """
                        UPDATE ocr_bolla_sessioni
                        SET cliente_scelto = %(cli)s,
                            match_json = %(match)s::jsonb,
                            image_path = COALESCE(image_path, %(path)s),
                            updated_at = now()
                        WHERE id = %(id)s
                        """,
                        {
                            "cli": result["codice_cliente"],
                            "match": match_json,
                            "path": image_path,
                            "id": session_id,
                        },
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO ocr_bolla_sessioni (
                          username, image_sha256, mime_type, image_bytes, image_path, model,
                          openai_response_id, ocr_json, cliente_scelto, match_json
                        ) VALUES (
                          %(user)s, %(sha)s, %(mime)s, %(size)s, %(path)s, %(model)s,
                          %(rid)s, %(ocr)s::jsonb, %(cli)s, %(match)s::jsonb
                        ) RETURNING id
                        """,
                        {
                            "user": _username(),
                            "sha": sha,
                            "mime": persist_mime,
                            "size": len(image),
                            "path": image_path,
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
            _log(f"done session_id={session_id} cliente={result.get('codice_cliente')}")
        except Exception as e:
            conn.rollback()
            _log(f"matching Exception: {e}")
            traceback.print_exc(file=sys.stderr)
            response.status = 500
            return {"error": f"Errore matching: {e}", "ocr": ocr}
        finally:
            db_pool.release_conn(conn)

        return {
            "session_id": session_id,
            "cached": bool(cached),
            "model": model,
            "source_mime": source_mime,
            "pdf_pages_used": prepared.get("pdf_pages_used"),
            "pdf_pages_total": prepared.get("pdf_pages_total"),
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
                        "match": json.dumps({
                            k: result[k] for k in ("cliente", "righe_match", "capabilities")
                        }),
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
