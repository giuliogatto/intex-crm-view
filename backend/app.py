from bottle import Bottle, request, response, HTTPResponse
from database import DatabasePool
from datetime import datetime
import json

from auth import authenticate_user, create_token, get_current_user, hash_password
from prompts import genericPrompt, replace_oggi_placeholder
from LLMservice import send_prompt, get_model_name
from pdf_export import build_pdf
from stagioni_aliases import apply_stagione_filter, build_stagioni_api_list, stagione_display_label

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


def _format_euro(value):
    return f"€ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _pdf_response(pdf_bytes, filename):
    return HTTPResponse(
        body=pdf_bytes,
        status=200,
        headers={
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{filename}"',
        },
    )


def _list_filters():
    return {
        'data_inizio': parse_date(request.query.get('data_inizio')),
        'data_fine': parse_date(request.query.get('data_fine')),
        'codice_cliente': request.query.get('codice_cliente'),
        'ragione_sociale': request.query.get('ragione_sociale'),
        'stagione': request.query.get('stagione'),
        'stato': request.query.get('stato'),
    }


def _paginated_list_response(items, total, page, limit, totals=None):
    pages = max((total + limit - 1) // limit, 1) if total else 1
    result = {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "data": items,
    }
    if totals is not None:
        result["totals"] = totals
    return result


def _filters_are_active(filters, tab=None):
    if filters.get('data_inizio') or filters.get('data_fine'):
        return True
    if filters.get('codice_cliente') or filters.get('ragione_sociale'):
        return True
    if filters.get('stagione'):
        return True
    stato = filters.get('stato')
    if stato:
        if tab == 'offerte' and stato != 'Tutti':
            return True
    return False


def _compute_list_totals(cursor, from_where_fn, field_map, filters):
    """Aggregate numeric columns for the full filtered result set (not just the current page)."""
    from_where, params = from_where_fn(filters)
    select_parts = [f"{expr} AS {key}" for key, expr in field_map.items()]
    cursor.execute(f"SELECT {', '.join(select_parts)} {from_where}", params)
    row = cursor.fetchone()
    return {key: float(row[i]) for i, key in enumerate(field_map)}


FATTURE_TOTAL_FIELDS = {
    'importo_documento': 'COALESCE(SUM(f.importo_totale), 0)',
}

OFFERTE_TOTAL_FIELDS = {
    'importo': 'COALESCE(SUM(o.importo_totale), 0)',
}

PUBLIC_PATHS = {'/health', '/api/auth/login'}

# CORS Headers Hooks
@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, OPTIONS'
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

        stagioni = build_stagioni_api_list(rows)
        return {"total": len(stagioni), "data": stagioni}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 2. DDT / Bolle List
def _bolle_from_where(filters):
    query = """
        FROM ddt_testate d
        JOIN clienti c ON d.codice_cliente = c.codice
        WHERE 1=1
    """
    params = {}

    if filters['data_inizio']:
        query += " AND d.data_bolla >= %(data_inizio)s"
        params['data_inizio'] = filters['data_inizio']
    if filters['data_fine']:
        query += " AND d.data_bolla <= %(data_fine)s"
        params['data_fine'] = filters['data_fine']
    if filters['codice_cliente'] and filters['codice_cliente'] != '':
        query += " AND d.codice_cliente = %(codice_cliente)s"
        params['codice_cliente'] = filters['codice_cliente']
    if filters['ragione_sociale'] and filters['ragione_sociale'] != '':
        query += " AND c.ragione_sociale ILIKE %(ragione_sociale)s"
        params['ragione_sociale'] = f"%{filters['ragione_sociale']}%"
    query, params = apply_stagione_filter(query, params, filters, "d.codice_stagione")

    return query, params


def _count_bolle(cursor, filters):
    from_where, params = _bolle_from_where(filters)
    cursor.execute(f"SELECT COUNT(*) {from_where}", params)
    return cursor.fetchone()[0]


def _fetch_bolle(cursor, filters, limit=None, offset=0):
    from_where, params = _bolle_from_where(filters)
    query = f"""
        SELECT d.numero_bolla, TO_CHAR(d.data_bolla, 'DD/MM/YYYY') as data_bolla,
               c.ragione_sociale, c.codice as codice_cliente,
               (SELECT COALESCE(string_agg(DISTINCT dr.numero_disposizione, ', '), '—')
                FROM ddt_righe dr WHERE dr.numero_bolla = d.numero_bolla) as righe_collegate
        {from_where}
        ORDER BY d.data_bolla DESC, d.numero_bolla DESC
    """
    if limit is not None:
        query += " LIMIT %(limit)s OFFSET %(offset)s"
        params = {**params, 'limit': limit, 'offset': offset}

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [
        {
            "numero_bolla": r[0],
            "data": r[1],
            "cliente": r[2],
            "codice_cliente": r[3],
            "righe_collegate": r[4],
        }
        for r in rows
    ]


@app.route('/api/bolle', method='GET')
def get_bolle():
    try:
        filters = _list_filters()
        page, limit, offset = parse_pagination(default_limit=50, max_limit=50)
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        total = _count_bolle(cursor, filters)
        bolle = _fetch_bolle(cursor, filters, limit=limit, offset=offset)
        cursor.close()
        db_pool.release_conn(conn)
        return _paginated_list_response(bolle, total, page, limit)
    except Exception as e:
        response.status = 500
        return {"error": str(e)}


@app.route('/api/bolle/<id>', method='GET')
def get_bolla_detail(id):
    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        header_query = """
            SELECT d.numero_bolla, TO_CHAR(d.data_bolla, 'DD/MM/YYYY') as data_bolla,
                   c.ragione_sociale, c.codice as codice_cliente,
                   COALESCE((SELECT SUM(dr.importo_riga) FROM ddt_righe dr WHERE dr.numero_bolla = d.numero_bolla), 0) as importo_totale
            FROM ddt_testate d
            JOIN clienti c ON d.codice_cliente = c.codice
            WHERE d.numero_bolla = %(numero_bolla)s
        """
        cursor.execute(header_query, {"numero_bolla": id})
        header_row = cursor.fetchone()

        if not header_row:
            cursor.close()
            db_pool.release_conn(conn)
            response.status = 404
            return {"error": "Bolla non trovata"}

        lines_query = """
            SELECT dr.riga_num, dr.numero_disposizione, dr.riga_disposizione,
                   dr.numero_offerta, dr.codice_articolo, dr.colore,
                   dr.kg_consegnati, dr.capi_consegnati, dr.importo_riga
            FROM ddt_righe dr
            WHERE dr.numero_bolla = %(numero_bolla)s
            ORDER BY dr.riga_num
        """
        cursor.execute(lines_query, {"numero_bolla": id})
        lines_rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        header = {
            "numero_bolla": header_row[0],
            "data": header_row[1],
            "cliente": header_row[2],
            "codice_cliente": header_row[3],
            "importo_totale": float(header_row[4]),
        }

        lines = [
            {
                "riga_num": r[0],
                "numero_disposizione": r[1] or '—',
                "riga_disposizione": r[2] if r[2] is not None else '—',
                "numero_offerta": r[3] or '—',
                "articolo": r[4],
                "colore": r[5],
                "kg_consegnati": float(r[6]),
                "capi_consegnati": int(r[7]),
                "importo_riga": float(r[8]),
            }
            for r in lines_rows
        ]

        return {"header": header, "lines": lines}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}


@app.route('/api/bolle/export/pdf', method='GET')
def export_bolle_pdf():
    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        bolle = _fetch_bolle(cursor, _list_filters())
        cursor.close()
        db_pool.release_conn(conn)

        headers = ['N. bolla', 'Data', 'Cliente', 'Codice Cliente', 'Righe collegate']
        rows = [
            [b['numero_bolla'], b['data'], b['cliente'], b['codice_cliente'], b['righe_collegate']]
            for b in bolle
        ]
        pdf_bytes = build_pdf('Bolle / DDT — Esportazione', headers, rows)
        return _pdf_response(pdf_bytes, 'bolle_esportazione.pdf')
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 3. Invoices / Fatture List
def _fatture_from_where(filters):
    query = """
        FROM fatture_testate f
        JOIN clienti c ON f.codice_cliente = c.codice
        WHERE 1=1
    """
    params = {}

    if filters['data_inizio']:
        query += " AND f.data_fattura >= %(data_inizio)s"
        params['data_inizio'] = filters['data_inizio']
    if filters['data_fine']:
        query += " AND f.data_fattura <= %(data_fine)s"
        params['data_fine'] = filters['data_fine']
    if filters['codice_cliente'] and filters['codice_cliente'] != '':
        query += " AND f.codice_cliente = %(codice_cliente)s"
        params['codice_cliente'] = filters['codice_cliente']
    if filters['ragione_sociale'] and filters['ragione_sociale'] != '':
        query += " AND c.ragione_sociale ILIKE %(ragione_sociale)s"
        params['ragione_sociale'] = f"%{filters['ragione_sociale']}%"
    query, params = apply_stagione_filter(query, params, filters, "f.codice_stagione")

    return query, params


def _count_fatture(cursor, filters):
    from_where, params = _fatture_from_where(filters)
    cursor.execute(f"SELECT COUNT(*) {from_where}", params)
    return cursor.fetchone()[0]


def _fetch_fatture(cursor, filters, limit=None, offset=0):
    from_where, params = _fatture_from_where(filters)
    query = f"""
        SELECT f.numero_disposizione, TO_CHAR(f.data_fattura, 'DD/MM/YYYY') as data_fattura,
               c.ragione_sociale, c.codice as codice_cliente, f.importo_totale
        {from_where}
        ORDER BY f.data_fattura DESC, f.numero_disposizione DESC
    """
    if limit is not None:
        query += " LIMIT %(limit)s OFFSET %(offset)s"
        params = {**params, 'limit': limit, 'offset': offset}

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [
        {
            "numero_disposizione": r[0],
            "data": r[1],
            "cliente": r[2],
            "codice_cliente": r[3],
            "importo_documento": float(r[4]),
        }
        for r in rows
    ]


@app.route('/api/fatture', method='GET')
def get_fatture():
    try:
        filters = _list_filters()
        page, limit, offset = parse_pagination(default_limit=50, max_limit=50)
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        total = _count_fatture(cursor, filters)
        fatture = _fetch_fatture(cursor, filters, limit=limit, offset=offset)
        totals = None
        if _filters_are_active(filters, 'fatture'):
            totals = _compute_list_totals(cursor, _fatture_from_where, FATTURE_TOTAL_FIELDS, filters)
        cursor.close()
        db_pool.release_conn(conn)
        return _paginated_list_response(fatture, total, page, limit, totals=totals)
    except Exception as e:
        response.status = 500
        return {"error": str(e)}


@app.route('/api/fatture/export/pdf', method='GET')
def export_fatture_pdf():
    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        fatture = _fetch_fatture(cursor, _list_filters())
        cursor.close()
        db_pool.release_conn(conn)

        headers = ['N. disp.', 'Periodo riferimento', 'Cliente', 'Codice Cliente', 'Importo documento']
        rows = [
            [
                f['numero_disposizione'],
                f['data'],
                f['cliente'],
                f['codice_cliente'],
                _format_euro(f['importo_documento']),
            ]
            for f in fatture
        ]
        pdf_bytes = build_pdf('Fatture — Esportazione', headers, rows)
        return _pdf_response(pdf_bytes, 'fatture_esportazione.pdf')
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 4. Invoice Detail (Rows)
@app.route('/api/fatture/<id>', method='GET')
def get_fattura_detail(id):
    try:
        codice_cliente = (request.query.get('codice_cliente') or '').strip()
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        header_query = """
            SELECT f.numero_disposizione, TO_CHAR(f.data_fattura, 'DD/MM/YYYY') as data_fattura,
                   c.ragione_sociale, c.codice as codice_cliente, f.importo_totale
            FROM fatture_testate f
            JOIN clienti c ON f.codice_cliente = c.codice
            WHERE f.numero_disposizione = %(numero_disp)s
        """
        header_params = {"numero_disp": id}
        if codice_cliente:
            header_query += " AND f.codice_cliente = %(codice_cliente)s"
            header_params["codice_cliente"] = codice_cliente
        cursor.execute(header_query, header_params)
        header_row = cursor.fetchone()

        if not header_row and not codice_cliente:
            cursor.execute(
                """
                SELECT f.numero_disposizione, TO_CHAR(f.data_fattura, 'DD/MM/YYYY') as data_fattura,
                       c.ragione_sociale, c.codice as codice_cliente, f.importo_totale
                FROM fatture_testate f
                JOIN clienti c ON f.codice_cliente = c.codice
                WHERE f.numero_disposizione = %(numero_disp)s
                """,
                {"numero_disp": id},
            )
            matches = cursor.fetchall()
            if len(matches) == 1:
                header_row = matches[0]

        if not header_row:
            cursor.close()
            db_pool.release_conn(conn)
            response.status = 404
            return {"error": "Fattura non trovata"}

        codice_cliente = header_row[3]

        lines_query = """
            SELECT r.riga_disposizione, 
                   COALESCE((SELECT TO_CHAR(d.data_bolla, 'DD/MM/YYYY') FROM ddt_testate d WHERE d.numero_bolla = r.numero_bolla), '—') as data_bolla,
                   r.numero_bolla, r.codice_articolo, r.colore, r.kg_fatturati, r.capi_fatturati, r.importo_riga
            FROM fatture_righe r
            WHERE r.codice_cliente = %(codice_cliente)s
              AND r.numero_disposizione = %(numero_disp)s
            ORDER BY r.riga_disposizione
        """
        cursor.execute(lines_query, {"numero_disp": id, "codice_cliente": codice_cliente})
        lines_rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        header = {
            "numero_disposizione": header_row[0],
            "data": header_row[1],
            "cliente": header_row[2],
            "codice_cliente": header_row[3],
            "importo_totale": float(header_row[4]),
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
def _offerte_from_where(filters):
    query = """
        FROM offerte_testate o
        JOIN clienti c ON o.codice_cliente = c.codice
        WHERE 1=1
    """
    params = {}

    if filters['data_inizio']:
        query += " AND o.data_offerta >= %(data_inizio)s"
        params['data_inizio'] = filters['data_inizio']
    if filters['data_fine']:
        query += " AND o.data_offerta <= %(data_fine)s"
        params['data_fine'] = filters['data_fine']
    if filters['codice_cliente'] and filters['codice_cliente'] != '':
        query += " AND o.codice_cliente = %(codice_cliente)s"
        params['codice_cliente'] = filters['codice_cliente']
    if filters['ragione_sociale'] and filters['ragione_sociale'] != '':
        query += " AND c.ragione_sociale ILIKE %(ragione_sociale)s"
        params['ragione_sociale'] = f"%{filters['ragione_sociale']}%"
    query, params = apply_stagione_filter(query, params, filters, "o.codice_stagione")
    if filters['stato'] and filters['stato'] != '' and filters['stato'] != 'Tutti':
        query += " AND o.stato = %(stato)s"
        params['stato'] = filters['stato']

    return query, params


def _count_offerte(cursor, filters):
    from_where, params = _offerte_from_where(filters)
    cursor.execute(f"SELECT COUNT(*) {from_where}", params)
    return cursor.fetchone()[0]


def _fetch_offerte(cursor, filters, limit=None, offset=0):
    from_where, params = _offerte_from_where(filters)
    query = f"""
        SELECT o.numero_offerta, TO_CHAR(o.data_offerta, 'DD/MM/YYYY') as data_offerta,
               c.ragione_sociale, c.codice as codice_cliente, o.importo_totale, o.stato,
               o.codice_stagione
        {from_where}
        ORDER BY o.data_offerta DESC, o.numero_offerta DESC
    """
    if limit is not None:
        query += " LIMIT %(limit)s OFFSET %(offset)s"
        params = {**params, 'limit': limit, 'offset': offset}

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [
        {
            "numero_offerta": r[0],
            "data": r[1],
            "cliente": r[2],
            "codice_cliente": r[3],
            "importo": float(r[4]),
            "stato": r[5],
            "stagione": stagione_display_label(r[6]),
        }
        for r in rows
    ]


@app.route('/api/offerte', method='GET')
def get_offerte():
    try:
        filters = _list_filters()
        page, limit, offset = parse_pagination(default_limit=50, max_limit=50)
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        total = _count_offerte(cursor, filters)
        offerte = _fetch_offerte(cursor, filters, limit=limit, offset=offset)
        totals = None
        if _filters_are_active(filters, 'offerte'):
            totals = _compute_list_totals(cursor, _offerte_from_where, OFFERTE_TOTAL_FIELDS, filters)
        cursor.close()
        db_pool.release_conn(conn)
        return _paginated_list_response(offerte, total, page, limit, totals=totals)
    except Exception as e:
        response.status = 500
        return {"error": str(e)}


@app.route('/api/offerte/<id>', method='GET')
def get_offerta_detail(id):
    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        header_query = """
            SELECT o.numero_offerta, TO_CHAR(o.data_offerta, 'DD/MM/YYYY') as data_offerta,
                   c.ragione_sociale, c.codice as codice_cliente, o.importo_totale, o.stato,
                   o.codice_stagione
            FROM offerte_testate o
            JOIN clienti c ON o.codice_cliente = c.codice
            WHERE o.numero_offerta = %(numero_offerta)s
        """
        cursor.execute(header_query, {"numero_offerta": id})
        header_row = cursor.fetchone()

        if not header_row:
            cursor.close()
            db_pool.release_conn(conn)
            response.status = 404
            return {"error": "Offerta non trovata"}

        lines_query = """
            SELECT r.riga_num, r.codice_articolo, r.colore, r.quantita, r.prezzo_unitario, r.importo_riga
            FROM offerte_righe r
            WHERE r.numero_offerta = %(numero_offerta)s
            ORDER BY r.riga_num
        """
        cursor.execute(lines_query, {"numero_offerta": id})
        lines_rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        header = {
            "numero_offerta": header_row[0],
            "data": header_row[1],
            "cliente": header_row[2],
            "codice_cliente": header_row[3],
            "importo_totale": float(header_row[4]),
            "stato": header_row[5],
            "stagione": stagione_display_label(header_row[6]),
        }

        lines = [
            {
                "riga_num": r[0],
                "articolo": r[1],
                "colore": r[2],
                "quantita": float(r[3]),
                "prezzo_unitario": float(r[4]),
                "importo_riga": float(r[5]),
            }
            for r in lines_rows
        ]

        return {"header": header, "lines": lines}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}


@app.route('/api/offerte/export/pdf', method='GET')
def export_offerte_pdf():
    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        offerte = _fetch_offerte(cursor, _list_filters())
        cursor.close()
        db_pool.release_conn(conn)

        headers = ['N. offerta', 'Data', 'Cliente', 'Codice Cliente', 'Stagione', 'Importo', 'Stato']
        rows = [
            [
                o['numero_offerta'],
                o['data'],
                o['cliente'],
                o['codice_cliente'],
                o['stagione'],
                _format_euro(o['importo']),
                o['stato'],
            ]
            for o in offerte
        ]
        pdf_bytes = build_pdf('Offerte / Ordini — Esportazione', headers, rows)
        return _pdf_response(pdf_bytes, 'offerte_esportazione.pdf')
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

# 6. Auditing Discrepancies (Compare Offer vs DDT vs Invoice)
def _fetch_discrepanze(cursor, codice_cliente):
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
            (COALESCE(SUM(fr.capi_fatturati), 0) - COALESCE(SUM(dr.capi_consegnati), 0)) AS diff_capi,
            (COALESCE(SUM(dr.importo_riga), 0) - COALESCE(SUM(fr.importo_riga), 0)) AS diff_valore
        FROM ddt_righe dr
        JOIN ddt_testate dt ON dr.numero_bolla = dt.numero_bolla
        LEFT JOIN articoli art ON dr.codice_articolo = art.codice
        LEFT JOIN fatture_righe fr ON dr.numero_disposizione = fr.numero_disposizione
                                   AND dt.codice_cliente = fr.codice_cliente
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
    return [
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
            "diff_valore": float(r[12]),
        }
        for r in rows
    ]


@app.route('/api/discrepanze', method='GET')
def get_discrepanze():
    codice_cliente = request.query.get('codice_cliente')
    if not codice_cliente or codice_cliente == '':
        codice_cliente = 'XXX'

    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        discrepanze = _fetch_discrepanze(cursor, codice_cliente)
        cursor.close()
        db_pool.release_conn(conn)
        return {"total": len(discrepanze), "data": discrepanze}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}


@app.route('/api/discrepanze/export/pdf', method='GET')
def export_discrepanze_pdf():
    codice_cliente = request.query.get('codice_cliente')
    if not codice_cliente or codice_cliente == '':
        codice_cliente = 'XXX'

    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        discrepanze = _fetch_discrepanze(cursor, codice_cliente)
        cursor.close()
        db_pool.release_conn(conn)

        headers = [
            'Articolo', 'Colore', 'Capi Offerti', 'Valore Offerto', 'Capi Consegnati',
            'Kg Consegnati', 'Valore Consegnato', 'Capi Fatturati', 'Kg Fatturati',
            'Valore Fatturato', 'Diff Capi', 'Diff Valore',
        ]
        rows = [
            [
                d['articolo_desc'],
                d['colore'],
                d['capi_offerti'],
                _format_euro(d['valore_offerto']),
                d['capi_consegnati'],
                d['kg_consegnati'],
                _format_euro(d['valore_consegnato']),
                d['capi_fatturati'],
                d['kg_fatturati'],
                _format_euro(d['valore_fatturato']),
                d['diff_capi'],
                _format_euro(d['diff_valore']),
            ]
            for d in discrepanze
        ]
        pdf_bytes = build_pdf(
            f'Auditing Discrepanze — Cliente {codice_cliente}',
            headers,
            rows,
            col_widths=[0.8, 3.2] + [1] * 10,
        )
        return _pdf_response(pdf_bytes, f'discrepanze_audit_{codice_cliente}.pdf')
    except Exception as e:
        response.status = 500
        return {"error": str(e)}

VALID_USER_ROLES = {'admin', 'user'}


def _require_admin():
    current_user = _get_request_user()
    if not current_user or current_user.get('role') != 'admin':
        response.status = 403
        return None, {"error": "Admin access required"}
    return current_user, None


# 7. Users (admin only)
@app.route('/api/users', method='GET')
def list_users():
    denied = _require_admin()
    if denied[0] is None:
        return denied[1]

    try:
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, role, is_active,
                   TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI:SS') AS created_at
            FROM users
            ORDER BY username
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        db_pool.release_conn(conn)

        users = [
            {
                "id": r[0],
                "username": r[1],
                "role": r[2],
                "is_active": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
        return {"data": users}
    except Exception as e:
        response.status = 500
        return {"error": str(e)}


@app.route('/api/users', method='POST')
def create_user():
    denied = _require_admin()
    if denied[0] is None:
        return denied[1]

    try:
        data = request.json
        if not data:
            response.status = 400
            return {"error": "Invalid request body"}

        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        role = (data.get('role') or 'user').strip()

        if not username or not password:
            response.status = 400
            return {"error": "Username and password are required"}
        if role not in VALID_USER_ROLES:
            response.status = 400
            return {"error": "Invalid role"}

        conn = db_pool.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (%(username)s, %(password_hash)s, %(role)s)
            RETURNING id, username, role, is_active,
                      TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI:SS') AS created_at
            """,
            {
                "username": username,
                "password_hash": hash_password(password),
                "role": role,
            },
        )
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        db_pool.release_conn(conn)

        return {
            "user": {
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "is_active": row[3],
                "created_at": row[4],
            }
        }
    except Exception as e:
        if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            response.status = 409
            return {"error": "Username already exists"}
        response.status = 500
        return {"error": str(e)}


@app.route('/api/users/<user_id>', method='PATCH')
def update_user(user_id):
    denied = _require_admin()
    if denied[0] is None:
        return denied[1]

    try:
        data = request.json
        if not data:
            response.status = 400
            return {"error": "Invalid request body"}

        password = data.get('password')
        role = data.get('role')
        is_active = data.get('is_active')

        if password is None and role is None and is_active is None:
            response.status = 400
            return {"error": "No fields to update"}

        if role is not None and role not in VALID_USER_ROLES:
            response.status = 400
            return {"error": "Invalid role"}

        updates = []
        params = {"user_id": user_id}

        if password is not None:
            if not password:
                response.status = 400
                return {"error": "Password cannot be empty"}
            updates.append("password_hash = %(password_hash)s")
            params["password_hash"] = hash_password(password)

        if role is not None:
            updates.append("role = %(role)s")
            params["role"] = role

        if is_active is not None:
            updates.append("is_active = %(is_active)s")
            params["is_active"] = bool(is_active)

        conn = db_pool.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE id = %(user_id)s
            RETURNING id, username, role, is_active,
                      TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI:SS') AS created_at
            """,
            params,
        )
        row = cursor.fetchone()
        if not row:
            cursor.close()
            db_pool.release_conn(conn)
            response.status = 404
            return {"error": "User not found"}

        conn.commit()
        cursor.close()
        db_pool.release_conn(conn)

        return {
            "user": {
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "is_active": row[3],
                "created_at": row[4],
            }
        }
    except Exception as e:
        response.status = 500
        return {"error": str(e)}


# 8. Chats List (paginated, admin only)
@app.route('/api/chats', method='GET')
def get_chats():
    denied = _require_admin()
    if denied[0] is None:
        return denied[1]

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


# 9. Chat Messages (paginated, admin only)
@app.route('/api/chats/<chat_id>/messages', method='GET')
def get_chat_messages(chat_id):
    denied = _require_admin()
    if denied[0] is None:
        return denied[1]

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


ROOT_PROVIDER_MESSAGE_ID = "root"


def _get_request_user():
    return request.environ.get('intex.user')


def _chat_user_id(user):
    return user['username']


def _user_can_access_chat(user, chat_user_id):
    return user.get('role') == 'admin' or chat_user_id == _chat_user_id(user)


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
        current_user = _get_request_user()
        user_id = _chat_user_id(current_user)
        chat_id = data.get('chat_id')
        model = get_model_name()
        instructions = replace_oggi_placeholder(genericPrompt)

        conn = db_pool.get_conn()
        cursor = conn.cursor()

        previous_response_id = None
        history = None

        if chat_id is not None:
            cursor.execute(
                "SELECT id, user_id FROM chats WHERE id = %(chat_id)s",
                {"chat_id": chat_id},
            )
            chat_row = cursor.fetchone()
            if not chat_row:
                cursor.close()
                db_pool.release_conn(conn)
                response.status = 404
                return {"error": f"Chat {chat_id} not found"}

            if not _user_can_access_chat(current_user, chat_row[1]):
                cursor.close()
                db_pool.release_conn(conn)
                response.status = 403
                return {"error": "Access denied to this chat"}

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
