from bottle import Bottle, response
from database import DatabasePool

app = Bottle()
db_pool = DatabasePool()

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

# Catch-all route for undefined routes
@app.route('/<:re:.*>')
def catch_all():
    response.status = 404
    return "Nothing to see here"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)


