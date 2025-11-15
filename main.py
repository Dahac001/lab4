from flask import Flask, request, jsonify
import os
from urllib.parse import urlparse

app = Flask(__name__)

# Попробуем импортировать psycopg2 с обработкой ошибок
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
    print("✅ psycopg2 imported successfully")
except ImportError as e:
    print(f"❌ psycopg2 import failed: {e}")
    PSYCOPG2_AVAILABLE = False
    # Покажем альтернативное сообщение
    print("⚠️  Database features will be disabled")

# Функция для подключения к БД
def get_db_connection():
    if not PSYCOPG2_AVAILABLE:
        print("❌ psycopg2 not available - database disabled")
        return None
        
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found")
        return None
    
    try:
        url = urlparse(DATABASE_URL)
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        print("✅ Database connected successfully!")
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

# Подключение к БД
conn = get_db_connection()

# Создание таблицы
if conn:
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
            print("✅ Table created successfully")
    except Exception as e:
        print(f"❌ Table creation error: {e}")

# Временное хранилище (на случай если БД не работает)
temp_storage = []

@app.route('/')
def hello():
    db_status = "connected" if conn else "disconnected"
    return f"🚀 Hello, Serverless! Database: {db_status}\n", 200

@app.route('/echo', methods=['POST'])
def echo():
    data = request.get_json()
    return jsonify({
        "status": "received",
        "you_sent": data,
        "database": "available" if PSYCOPG2_AVAILABLE else "unavailable"
    })

@app.route('/save', methods=['POST'])
def save_message():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data"}), 400
    
    message = data.get('message', '')
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    # Пробуем сохранить в БД, если доступна
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO messages (content) VALUES (%s)", (message,))
                conn.commit()
            return jsonify({
                "status": "saved to database",
                "message": message,
                "storage": "postgresql"
            })
        except Exception as e:
            return jsonify({"error": f"Database error: {str(e)}"}), 500
    else:
        # Сохраняем во временное хранилище
        temp_storage.append(message)
        return jsonify({
            "status": "saved to memory",
            "message": message,
            "storage": "temporary memory",
            "note": "Database not available"
        })

@app.route('/messages')
def get_messages():
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, content, created_at FROM messages ORDER BY id DESC LIMIT 10")
                rows = cur.fetchall()
            messages = [{"id": r[0], "text": r[1], "time": str(r[2])} for r in rows]
            return jsonify({
                "status": "from database",
                "count": len(messages),
                "messages": messages
            })
        except Exception as e:
            return jsonify({"error": f"Database error: {str(e)}"}), 500
    else:
        return jsonify({
            "status": "from memory",
            "count": len(temp_storage),
            "messages": temp_storage,
            "note": "Database not available - using temporary storage"
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)