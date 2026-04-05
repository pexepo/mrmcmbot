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
from bot import bot, LOG_CHANNEL_ID

app = Flask(__name__)
app.secret_key = os.getenv("ADMIN_SECRET_KEY", "change-this-secret-key-in-production")

# Админ логин/пароль из переменных окружения
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def login_required(f):
    """Декоратор для проверки авторизации."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


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
async def download_media(file_id):
    """Скачивание медиа в максимальном качестве."""
    try:
        file = await bot.get_file(file_id)
        file_path = file.file_path

        # Получаем файл через Telegram Bot API
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

        return redirect(file_url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    app.run(host="0.0.0.0", port=port, debug=False)
