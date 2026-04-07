from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    session,
    send_file,
)
from functools import wraps
import os
from database import (
    get_all_users,
    get_active_users,
    get_logs,
    get_media_submissions,
    get_stats,
)

# Конфигурация (без импорта bot, чтобы избежать конфликта токенов)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8579457514:AAEAzcBbCpf4Lq9wj762cKhzzdjEXjf_Zso")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1003626245326"))

app = Flask(__name__)
app.secret_key = os.getenv("ADMIN_SECRET_KEY", "change-this-secret-key-in-production")

# Админ логин/пароль из переменных окружения
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


# Middleware для логирования всех запросов
@app.before_request
def log_request():
    print(
        f">>> Incoming request: {request.method} {request.path} from {request.remote_addr}"
    )


@app.after_request
def log_response(response):
    print(f"<<< Response: {response.status_code} for {request.path}")
    return response


def login_required(f):
    """Декоратор для проверки авторизации."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/health")
def health():
    """Health check endpoint для BotHost."""
    return jsonify({"status": "ok"}), 200


@app.route("/login", methods=["GET", "POST"])
def login():
    """Страница входа."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Неверный логин или пароль")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Выход."""
    session.pop("logged_in", None)
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    """Главная страница панели."""
    stats = get_stats()
    return render_template("dashboard.html", stats=stats)


@app.route("/users")
@login_required
def users():
    """Страница всех пользователей."""
    all_users = get_all_users()
    return render_template("users.html", users=all_users)


@app.route("/users/active")
@login_required
def active_users():
    """Страница активных пользователей."""
    hours = request.args.get("hours", 24, type=int)
    users = get_active_users(hours)
    return render_template("active_users.html", users=users, hours=hours)


@app.route("/logs")
@login_required
def logs():
    """Страница логов."""
    log_type = request.args.get("type", None)
    limit = request.args.get("limit", 100, type=int)
    logs_data = get_logs(log_type, limit)
    return render_template("logs.html", logs=logs_data, log_type=log_type)


@app.route("/media")
@login_required
def media():
    """Страница медиа отправок."""
    limit = request.args.get("limit", 50, type=int)
    media_data = get_media_submissions(limit)
    return render_template(
        "media.html", media=media_data, log_channel_id=LOG_CHANNEL_ID
    )


@app.route("/media/<int:media_id>")
@login_required
def media_detail(media_id):
    """Детальная информация о работе."""
    import sqlite3
    from pathlib import Path

    DB_PATH = Path(__file__).parent / "bot_data.db"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT m.*, u.username, u.first_name, u.last_name
        FROM media_submissions m
        LEFT JOIN users u ON m.user_id = u.user_id
        WHERE m.id = ?
    """,
        (media_id,),
    )

    media = cursor.fetchone()
    conn.close()

    if not media:
        return "Работа не найдена", 404

    return render_template(
        "media_detail.html", media=dict(media), log_channel_id=LOG_CHANNEL_ID
    )


@app.route("/api/download/<file_id>")
@login_required
def download_media(file_id):
    """Скачивание медиа в максимальном качестве."""
    try:
        import requests
        import io
        from pathlib import Path

        print(f"[DOWNLOAD] Запрос на скачивание file_id: {file_id}")

        # Получаем информацию о файле через Telegram Bot API
        get_file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
        response = requests.get(get_file_url, params={"file_id": file_id}, timeout=10)

        print(f"[DOWNLOAD] getFile response status: {response.status_code}")
        print(f"[DOWNLOAD] getFile response: {response.text[:200]}")

        if response.status_code != 200:
            return jsonify(
                {
                    "error": "Не удалось получить информацию о файле",
                    "details": response.text,
                }
            ), 500

        result = response.json()
        if not result.get("ok"):
            return jsonify(
                {"error": "Telegram API вернул ошибку", "details": result}
            ), 500

        file_path = result["result"]["file_path"]
        print(f"[DOWNLOAD] file_path: {file_path}")

        # Скачиваем файл
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        print(f"[DOWNLOAD] Downloading from: {file_url[:80]}...")
        file_response = requests.get(file_url, timeout=30)

        print(f"[DOWNLOAD] Download response status: {file_response.status_code}")

        if file_response.status_code != 200:
            return jsonify(
                {
                    "error": "Не удалось скачать файл",
                    "status": file_response.status_code,
                }
            ), 500

        # Определяем имя файла и MIME тип
        filename = Path(file_path).name

        # Определяем MIME тип по расширению
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
        }

        file_ext = Path(filename).suffix.lower()
        mime_type = mime_types.get(file_ext, "application/octet-stream")

        print(
            f"[DOWNLOAD] Sending file: {filename}, mime: {mime_type}, size: {len(file_response.content)} bytes"
        )

        # Отправляем файл пользователю
        return send_file(
            io.BytesIO(file_response.content),
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename,
        )

    except requests.Timeout:
        print(f"[DOWNLOAD] Timeout error")
        return jsonify({"error": "Превышено время ожидания"}), 504
    except Exception as e:
        print(f"[DOWNLOAD] Exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Ошибка: {str(e)}"}), 500


@app.route("/api/stats")
@login_required
def api_stats():
    """API для получения статистики."""
    return jsonify(get_stats())


@app.route("/api/users")
@login_required
def api_users():
    """API для получения пользователей."""
    return jsonify(get_all_users())


@app.route("/api/logs")
@login_required
def api_logs():
    """API для получения логов."""
    log_type = request.args.get("type", None)
    limit = request.args.get("limit", 100, type=int)
    return jsonify(get_logs(log_type, limit))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"=== ADMIN PANEL STARTING ===")
    print(f"Port: {port}")
    print(f"Host: 0.0.0.0")
    print(f"Debug: False")
    print(f"===========================")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
