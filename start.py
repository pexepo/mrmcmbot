import subprocess
import sys
import os

if __name__ == "__main__":
    print("START.PY: Инициализация...")

    # Запускаем бота в отдельном процессе (без ожидания)
    print("START.PY: Запуск бота в фоновом процессе...")
    bot_process = subprocess.Popen(
        [sys.executable, "bot.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    # Сразу запускаем админ-панель в главном потоке (без задержки)
    print("START.PY: Запуск админ-панели в главном потоке...")
    from admin_panel import app

    port = int(os.environ.get("PORT", 5000))
    print(f"Flask запускается на порту {port}...")

    try:
        app.run(
            host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True
        )
    except KeyboardInterrupt:
        print("\nОстановка процессов...")
        bot_process.terminate()
        bot_process.wait()
        print("Все процессы остановлены.")
