from flask import Flask, request, jsonify
import psycopg2
import os
from urllib.parse import urlparse

app = Flask(__name__)

# Функция для подключения к базе данных
def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    print(f"DATABASE_URL: {DATABASE_URL}")  # Для отладки
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found!")
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
        print(f"❌ Database connection failed: {e}")
        return None

# Глобальное подключение
conn = get_db_connection()

# Создаем таблицу при запуске
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
            print("✅ Table 'messages' ready!")
    except Exception as e:
        print(f"❌ Table creation error: {e}")

# Маршрут 1: Главная страница
@app.route('/')
def hello():
    return "🚀 Hello, Serverless! Lab 4 is working!\n", 200, {'Content-Type': 'text/plain'}

# Маршрут 2: Эхо-эндпоинт
@app.route('/echo', methods=['POST'])
def echo():
    data = request.get_json()
    return jsonify({
        "status": "received",
        "you_sent": data,
        "length": len(str(data)) if data else 0
    })

# Маршрут 3: Сохранить сообщение в БД
@app.route('/save', methods=['POST'])
def save_message():
    if not conn:
        return jsonify({"error": "Database not connected"}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    message = data.get('message', '')
    if not message:
        return jsonify({"error": "Message field is required"}), 400
    
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO messages (content) VALUES (%s)", (message,))
            conn.commit()
        
        return jsonify({
            "status": "success", 
            "message": "Message saved to database",
            "saved_text": message
        })
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

# Маршрут 4: Получить сообщения из БД
@app.route('/messages')
def get_messages():
    if not conn:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, content, created_at FROM messages ORDER BY id DESC LIMIT 10")
            rows = cur.fetchall()
        
        messages = []
        for row in rows:
            messages.append({
                "id": row[0],
                "text": row[1],
                "time": row[2].isoformat() if row[2] else None
            })
        
        return jsonify({
            "status": "success",
            "count": len(messages),
            "messages": messages
        })
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

# Запуск приложения
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)