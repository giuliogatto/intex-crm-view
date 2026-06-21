from bottle import Bottle, request, response, HTTPResponse
from database import DatabasePool
from datetime import datetime
import json

from auth import authenticate_user, create_token, get_current_user
from prompts import genericPrompt, replace_oggi_placeholder
from LLMservice import send_prompt, get_model_name

app = Bottle()
db_pool = DatabasePool()

def parse_date(date_str):
    if not date_str:
        return None
    # Try DD/MM/YYYY and YYYY-MM-DD formats
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None


def parse_pagination(default_limit=20, max_limit=100):
    try:
        page = int(request.query.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = int(request.query.get('limit', default_limit))
    except (TypeError, ValueError):
        limit = default_limit

    page = max(page, 1)
    limit = max(min(limit, max_limit), 1)
    offset = (page - 1) * limit
    return page, limit, offset

PUBLIC_PATHS = {'/health', '/api/auth/login'}

# CORS Headers Hooks
@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, Authorization'

@app.hook('before_request')
def require_auth():
    if request.method == 'OPTIONS':
        return
    path = request.path
    if path in PUBLIC_PATHS:
        return
    if path.startswith('/api/') or path == '/llmrequest':
        user = get_current_user(db_pool)
        if not user:
            response.status = 401
            return {"error": "Authentication required"}
        request.environ['intex.user'] = user

@app.route('/<:re:.*>', method='OPTIONS')
def options_handler():
    response.status = 200
    return {}

@app.route('/api/auth/login', method='POST')
def auth_login():
    try:
        data = request.json
        if not data:
            response.status = 400
            return {"error": "Invalid request body"}

        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        if not username or not password:
            response.status = 400
            return {"error": "Username and password are required"}

        user = authenticate_user(db_pool, username, password)
        if not user:
            response.status = 401
            return {"error": "Invalid username or password"}

        token = create_token(user['id'], user['username'], user['role'])
        return {
            "token": token,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "role": user['role'],
            },
        }
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

@app.route('/api/auth/me', method='GET')
def auth_me():
    user = get_current_user(db_pool)
    if not user:
        response.status = 401
        return {"error": "Authentication required"}
    return {"user": user}

@app.route('/api/auth/logout', method='POST')
def auth_logout():
    return {"status": "ok"}

# Health & Database connection check
@app.route('/health')
def health():
    return {"status": "ok"}

@app.route('/db-test')
def db_test():
    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        cursor.close()
        db_pool.release_conn(conn)
        return {"status": "connected", "version": db_version[0]}
    except Exception as e:
        response.status = 500
        return {"status": "error", "message": str(e)}

# 1. Customers List
@app.route('/api/clienti', method='GET')
def get_clienti():
    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT codice, ragione_sociale FROM clienti ORDER BY ragione_sociale;")
        rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        clienti = [{"codice": r[0], "ragione_sociale": r[1]} for r in rows]
        return {"total": len(clienti), "data": clienti}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 1b. Seasons List
@app.route('/api/stagioni', method='GET')
def get_stagioni():
    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT codice, descrizione FROM stagioni ORDER BY codice DESC;")
        rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        stagioni = [{"codice": r[0], "descrizione": r[1]} for r in rows]
        return {"total": len(stagioni), "data": stagioni}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 2. DDT / Bolle List
@app.route('/api/bolle', method='GET')
def get_bolle():
    data_inizio = parse_date(request.query.get('data_inizio'))
    data_fine = parse_date(request.query.get('data_fine'))
    codice_cliente = request.query.get('codice_cliente')
    ragione_sociale = request.query.get('ragione_sociale')
    stagione = request.query.get('stagione')

    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        query = """
            SELECT d.numero_bolla, TO_CHAR(d.data_bolla, 'DD/MM/YYYY') as data_bolla, 
                   c.ragione_sociale, c.codice as codice_cliente,
                   (SELECT COALESCE(string_agg(DISTINCT dr.numero_disposizione, ', '), '—') 
                    FROM ddt_righe dr WHERE dr.numero_bolla = d.numero_bolla) as righe_collegate
            FROM ddt_testate d
            JOIN clienti c ON d.codice_cliente = c.codice
            WHERE 1=1
        """
        params = {}

        if data_inizio:
            query += " AND d.data_bolla >= %(data_inizio)s"
            params['data_inizio'] = data_inizio
        if data_fine:
            query += " AND d.data_bolla <= %(data_fine)s"
            params['data_fine'] = data_fine
        if codice_cliente and codice_cliente != '':
            query += " AND d.codice_cliente = %(codice_cliente)s"
            params['codice_cliente'] = codice_cliente
        if ragione_sociale and ragione_sociale != '':
            query += " AND c.ragione_sociale ILIKE %(ragione_sociale)s"
            params['ragione_sociale'] = f"%{ragione_sociale}%"
        if stagione and stagione != '':
            query += " AND d.codice_stagione ILIKE %(stagione)s"
            params['stagione'] = f"%{stagione}%"

        query += " ORDER BY d.data_bolla DESC, d.numero_bolla DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        bolle = [
            {
                "numero_bolla": r[0],
                "data": r[1],
                "cliente": r[2],
                "codice_cliente": r[3],
                "righe_collegate": r[4]
            } for r in rows
        ]
        return {"total": len(bolle), "data": bolle}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 3. Invoices / Fatture List
@app.route('/api/fatture', method='GET')
def get_fatture():
    data_inizio = parse_date(request.query.get('data_inizio'))
    data_fine = parse_date(request.query.get('data_fine'))
    codice_cliente = request.query.get('codice_cliente')
    ragione_sociale = request.query.get('ragione_sociale')
    stagione = request.query.get('stagione')
    stato = request.query.get('stato')

    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        query = """
            SELECT f.numero_disposizione, TO_CHAR(f.data_fattura, 'DD/MM/YYYY') as data_fattura,
                   c.ragione_sociale, c.codice as codice_cliente, f.importo_totale, f.stato_pagamento
            FROM fatture_testate f
            JOIN clienti c ON f.codice_cliente = c.codice
            WHERE 1=1
        """
        params = {}

        if data_inizio:
            query += " AND f.data_fattura >= %(data_inizio)s"
            params['data_inizio'] = data_inizio
        if data_fine:
            query += " AND f.data_fattura <= %(data_fine)s"
            params['data_fine'] = data_fine
        if codice_cliente and codice_cliente != '':
            query += " AND f.codice_cliente = %(codice_cliente)s"
            params['codice_cliente'] = codice_cliente
        if ragione_sociale and ragione_sociale != '':
            query += " AND c.ragione_sociale ILIKE %(ragione_sociale)s"
            params['ragione_sociale'] = f"%{ragione_sociale}%"
        if stagione and stagione != '':
            query += " AND f.codice_stagione ILIKE %(stagione)s"
            params['stagione'] = f"%{stagione}%"
        if stato and stato != '' and stato != 'Tutte':
            query += " AND f.stato_pagamento = %(stato)s"
            params['stato'] = stato

        query += " ORDER BY f.data_fattura DESC, f.numero_disposizione DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        fatture = [
            {
                "numero_disposizione": r[0],
                "data": r[1],
                "cliente": r[2],
                "codice_cliente": r[3],
                "importo_documento": float(r[4]),
                "stato": r[5]
            } for r in rows
        ]
        return {"total": len(fatture), "data": fatture}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 4. Invoice Detail (Rows)
@app.route('/api/fatture/<id>', method='GET')
def get_fattura_detail(id):
    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        # Get header
        header_query = """
            SELECT f.numero_disposizione, TO_CHAR(f.data_fattura, 'DD/MM/YYYY') as data_fattura,
                   c.ragione_sociale, c.codice as codice_cliente, f.importo_totale, f.stato_pagamento
            FROM fatture_testate f
            JOIN clienti c ON f.codice_cliente = c.codice
            WHERE f.numero_disposizione = %(numero_disp)s
        """
        cursor.execute(header_query, {"numero_disp": id})
        header_row = cursor.fetchone()

        if not header_row:
            cursor.close()
            db_pool.release_conn(conn)
            response.status = 404
            return {"error": "Fattura non trovata"}

        # Get lines
        lines_query = """
            SELECT r.riga_disposizione, 
                   COALESCE((SELECT TO_CHAR(d.data_bolla, 'DD/MM/YYYY') FROM ddt_testate d WHERE d.numero_bolla = r.numero_bolla), '—') as data_bolla,
                   r.numero_bolla, r.codice_articolo, r.colore, r.kg_fatturati, r.capi_fatturati, r.importo_riga
            FROM fatture_righe r
            WHERE r.numero_disposizione = %(numero_disp)s
            ORDER BY r.riga_disposizione
        """
        cursor.execute(lines_query, {"numero_disp": id})
        lines_rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        header = {
            "numero_disposizione": header_row[0],
            "data": header_row[1],
            "cliente": header_row[2],
            "codice_cliente": header_row[3],
            "importo_totale": float(header_row[4]),
            "stato": header_row[5]
        }

        lines = [
            {
                "riga_disposizione": r[0],
                "data_bolla": r[1],
                "numero_bolla": r[2],
                "articolo": r[3],
                "colore": r[4],
                "kg_fatturati": float(r[5]),
                "capi_fatturati": int(r[6]),
                "importo_riga": float(r[7])
            } for r in lines_rows
        ]

        return {"header": header, "lines": lines}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 5. Offers / Ordini List
@app.route('/api/offerte', method='GET')
def get_offerte():
    data_inizio = parse_date(request.query.get('data_inizio'))
    data_fine = parse_date(request.query.get('data_fine'))
    codice_cliente = request.query.get('codice_cliente')
    ragione_sociale = request.query.get('ragione_sociale')
    stagione = request.query.get('stagione')
    stato = request.query.get('stato')

    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        query = """
            SELECT o.numero_offerta, TO_CHAR(o.data_offerta, 'DD/MM/YYYY') as data_offerta,
                   c.ragione_sociale, c.codice as codice_cliente, o.importo_totale, o.stato,
                   COALESCE((SELECT descrizione FROM stagioni WHERE codice = o.codice_stagione), o.codice_stagione) as stagione_desc
            FROM offerte_testate o
            JOIN clienti c ON o.codice_cliente = c.codice
            WHERE 1=1
        """
        params = {}

        if data_inizio:
            query += " AND o.data_offerta >= %(data_inizio)s"
            params['data_inizio'] = data_inizio
        if data_fine:
            query += " AND o.data_offerta <= %(data_fine)s"
            params['data_fine'] = data_fine
        if codice_cliente and codice_cliente != '':
            query += " AND o.codice_cliente = %(codice_cliente)s"
            params['codice_cliente'] = codice_cliente
        if ragione_sociale and ragione_sociale != '':
            query += " AND c.ragione_sociale ILIKE %(ragione_sociale)s"
            params['ragione_sociale'] = f"%{ragione_sociale}%"
        if stagione and stagione != '':
            query += " AND o.codice_stagione ILIKE %(stagione)s"
            params['stagione'] = f"%{stagione}%"
        if stato and stato != '' and stato != 'Tutti':
            query += " AND o.stato = %(stato)s"
            params['stato'] = stato

        query += " ORDER BY o.data_offerta DESC, o.numero_offerta DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        offerte = [
            {
                "numero_offerta": r[0],
                "data": r[1],
                "cliente": r[2],
                "codice_cliente": r[3],
                "importo": float(r[4]),
                "stato": r[5],
                "stagione": r[6]
            } for r in rows
        ]
        return {"total": len(offerte), "data": offerte}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 6. Auditing Discrepancies (Compare Offer vs DDT vs Invoice)
@app.route('/api/discrepanze', method='GET')
def get_discrepanze():
    codice_cliente = request.query.get('codice_cliente')

    if not codice_cliente or codice_cliente == '':
        codice_cliente = 'XXX' # Default to TAM & COMPANY for demonstration

    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        query = """
            SELECT 
                art.codice AS articolo_codice,
                COALESCE(art.descrizione, dr.codice_articolo) AS articolo_desc,
                dr.colore,
                COALESCE(SUM(o_rig.quantita), 0) AS capi_offerti,
                COALESCE(SUM(o_rig.importo_riga), 0) AS valore_offerto,
                COALESCE(SUM(dr.capi_consegnati), 0) AS capi_consegnati,
                COALESCE(SUM(dr.kg_consegnati), 0) AS kg_consegnati,
                COALESCE(SUM(dr.importo_riga), 0) AS valore_consegnato,
                COALESCE(SUM(fr.capi_fatturati), 0) AS capi_fatturati,
                COALESCE(SUM(fr.kg_fatturati), 0) AS kg_fatturati,
                COALESCE(SUM(fr.importo_riga), 0) AS valore_fatturato,
                (COALESCE(SUM(dr.capi_consegnati), 0) - COALESCE(SUM(fr.capi_fatturati), 0)) AS diff_capi,
                (COALESCE(SUM(dr.importo_riga), 0) - COALESCE(SUM(fr.importo_riga), 0)) AS diff_valore
            FROM ddt_righe dr
            JOIN ddt_testate dt ON dr.numero_bolla = dt.numero_bolla
            LEFT JOIN articoli art ON dr.codice_articolo = art.codice
            LEFT JOIN fatture_righe fr ON dr.numero_disposizione = fr.numero_disposizione 
                                       AND dr.codice_articolo = fr.codice_articolo 
                                       AND dr.colore = fr.colore
            LEFT JOIN offerte_righe o_rig ON dr.numero_offerta = o_rig.numero_offerta 
                                          AND dr.codice_articolo = o_rig.codice_articolo 
                                          AND dr.colore = o_rig.colore
            WHERE dt.codice_cliente = %(codice_cliente)s
            GROUP BY art.codice, art.descrizione, dr.codice_articolo, dr.colore
            ORDER BY art.codice, dr.colore
        """

        cursor.execute(query, {"codice_cliente": codice_cliente})
        rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        discrepanze = [
            {
                "articolo_codice": r[0],
                "articolo_desc": r[1],
                "colore": r[2],
                "capi_offerti": float(r[3]),
                "valore_offerto": float(r[4]),
                "capi_consegnati": float(r[5]),
                "kg_consegnati": float(r[6]),
                "valore_consegnato": float(r[7]),
                "capi_fatturati": float(r[8]),
                "kg_fatturati": float(r[9]),
                "valore_fatturato": float(r[10]),
                "diff_capi": float(r[11]),
                "diff_valore": float(r[12])
            } for r in rows
        ]
        return {"total": len(discrepanze), "data": discrepanze}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 7. Chats List (paginated)
@app.route('/api/chats', method='GET')
def get_chats():
    page, limit, offset = parse_pagination(default_limit=20, max_limit=100)

    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM chats")
        total = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT c.id, c.user_id, c.model,
                   TO_CHAR(c.created_at, 'DD/MM/YYYY HH24:MI:SS') AS created_at,
                   (SELECT COUNT(*) FROM messages m WHERE m.chat_id = c.id) AS message_count
            FROM chats c
            ORDER BY c.created_at DESC, c.id DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {"limit": limit, "offset": offset},
        )
        rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        pages = max((total + limit - 1) // limit, 1) if total else 1
        chats = [
            {
                "id": r[0],
                "user_id": r[1],
                "model": r[2],
                "created_at": r[3],
                "message_count": r[4],
            }
            for r in rows
        ]
        return {"total": total, "page": page, "limit": limit, "pages": pages, "data": chats}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}


# 8. Chat Messages (paginated)
@app.route('/api/chats/<chat_id>/messages', method='GET')
def get_chat_messages(chat_id):
    page, limit, offset = parse_pagination(default_limit=50, max_limit=200)

    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_id, model,
                   TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI:SS') AS created_at
            FROM chats
            WHERE id = %(chat_id)s
            """,
            {"chat_id": chat_id},
        )
        chat_row = cursor.fetchone()
        if not chat_row:
            cursor.close()
            db_pool.release_conn(conn)
            response.status = 404
            return {"error": "Chat non trovata"}

        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE chat_id = %(chat_id)s",
            {"chat_id": chat_id},
        )
        total = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT id, role, content, provider_message_id,
                   TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI:SS') AS created_at
            FROM messages
            WHERE chat_id = %(chat_id)s
            ORDER BY id ASC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {"chat_id": chat_id, "limit": limit, "offset": offset},
        )
        rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        pages = max((total + limit - 1) // limit, 1) if total else 1
        chat = {
            "id": chat_row[0],
            "user_id": chat_row[1],
            "model": chat_row[2],
            "created_at": chat_row[3],
        }
        messages = [
            {
                "id": r[0],
                "role": r[1],
                "content": r[2],
                "provider_message_id": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
        return {
            "chat": chat,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
            "data": messages,
        }
    except Exception as e:
        response.status = 500
        return {"error": str(e)}


DEFAULT_USER_ID = "anonymous"
ROOT_PROVIDER_MESSAGE_ID = "root"


def _get_latest_assistant_response_id(cursor, chat_id):
    cursor.execute(
        """
        SELECT provider_message_id
        FROM messages
        WHERE chat_id = %(chat_id)s AND role = 'assistant'
        ORDER BY id DESC
        LIMIT 1
        """,
        {"chat_id": chat_id},
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _get_chat_history(cursor, chat_id):
    cursor.execute(
        """
        SELECT role, content
        FROM messages
        WHERE chat_id = %(chat_id)s
        ORDER BY id ASC
        """,
        {"chat_id": chat_id},
    )
    return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]


def _insert_message(cursor, chat_id, role, content, provider_message_id):
    cursor.execute(
        """
        INSERT INTO messages (chat_id, role, content, provider_message_id)
        VALUES (%(chat_id)s, %(role)s, %(content)s, %(provider_message_id)s)
        RETURNING id
        """,
        {
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "provider_message_id": provider_message_id,
        },
    )
    return cursor.fetchone()[0]


@app.route('/llmrequest', method='POST')
def llmrequest():
    conn = None
    try:
        data = request.json
        if not data or 'message' not in data:
            response.status = 400
            return {"error": "Missing required field: message"}

        user_query = data['message']
        if not isinstance(user_query, str) or not user_query.strip():
            response.status = 400
            return {"error": "Field 'message' must be a non-empty string"}

        user_query = user_query.strip()
        user_id = data.get('user_id') or DEFAULT_USER_ID
        chat_id = data.get('chat_id')
        model = get_model_name()
        instructions = replace_oggi_placeholder(genericPrompt)

        conn = db_pool.get_conn()
        cursor = conn.cursor()

        previous_response_id = None
        history = None

        if chat_id is not None:
            cursor.execute("SELECT id FROM chats WHERE id = %(chat_id)s", {"chat_id": chat_id})
            if not cursor.fetchone():
                cursor.close()
                db_pool.release_conn(conn)
                response.status = 404
                return {"error": f"Chat {chat_id} not found"}

            previous_response_id = _get_latest_assistant_response_id(cursor, chat_id)
            history = _get_chat_history(cursor, chat_id)
        else:
            cursor.execute(
                """
                INSERT INTO chats (user_id, model)
                VALUES (%(user_id)s, %(model)s)
                RETURNING id
                """,
                {"user_id": user_id, "model": model},
            )
            chat_id = cursor.fetchone()[0]

        user_provider_message_id = previous_response_id or ROOT_PROVIDER_MESSAGE_ID
        _insert_message(cursor, chat_id, "user", user_query, user_provider_message_id)

        if previous_response_id or history:
            llm_result = send_prompt(
                user_query,
                instructions=instructions,
                previous_response_id=previous_response_id,
                history=history,
            )
        else:
            # First turn: keep the legacy prompt shape so the user query follows
            # "Ecco la richiesta:" in the same input block.
            llm_result = send_prompt(replace_oggi_placeholder(genericPrompt + "\n" + user_query))
        llm_response = replace_oggi_placeholder(llm_result["text"])
        assistant_provider_message_id = llm_result["response_id"]

        _insert_message(
            cursor,
            chat_id,
            "assistant",
            llm_response,
            assistant_provider_message_id,
        )
        conn.commit()
        cursor.close()
        db_pool.release_conn(conn)
        conn = None

        try:
            response_json = json.loads(llm_response)
            print(json.dumps(response_json, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(llm_response)

        return {"response": llm_response, "chat_id": chat_id}
    except Exception as e:
        if conn is not None:
            conn.rollback()
            db_pool.release_conn(conn)
        response.status = 500
        return {"error": str(e)}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
