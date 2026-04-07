"""
Автоматический выбор базы данных.
Если установлена переменная DATABASE_URL - используется PostgreSQL.
Иначе - SQLite (для локальной разработки).
"""

import os

# Проверяем наличие DATABASE_URL
if os.getenv("DATABASE_URL"):
    print("🔄 Используется PostgreSQL")
    from database_postgres import *
else:
    print("🔄 Используется SQLite (локальная разработка)")
    from database_sqlite import *
