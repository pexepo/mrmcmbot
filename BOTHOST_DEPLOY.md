# 🚀 Гайд по деплою на Bothost

## Подготовка проекта

### 1. Создайте репозиторий на GitHub

1. Перейдите на https://github.com/new
2. Создайте новый репозиторий (например: `mrm-bot`)
3. Сделайте его приватным или публичным

### 2. Загрузите код в репозиторий

```bash
cd C:\Users\pexep\Downloads\booot

# Инициализация git (если еще не сделано)
git init

# Добавьте все файлы
git add .

# Создайте коммит
git commit -m "Initial commit"

# Подключите удаленный репозиторий
git remote add origin https://github.com/ваш_username/mrm-bot.git

# Отправьте код
git branch -M main
git push -u origin main
```

### 3. Создайте файл `.gitignore` (если его нет)

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
venv/
env/

# База данных (будет создана на хостинге)
*.db
*.sqlite

# Конфиденциальные данные
.env
bans.json
users.json

# IDE
.vscode/
.idea/
```

---

## Деплой БОТА на Bothost

### Шаг 1: Создание бота

1. Перейдите на https://bothost.ru
2. Войдите через Telegram
3. Нажмите **"Создать нового бота"**

### Шаг 2: Основные настройки

**Название бота:**
```
MRM Community Bot
```

**Платформа:**
```
✅ Telegram
```

**Библиотека:**
```
✅ Python
```

**Версия Python:**
```
3.11 (рекомендуется)
```

### Шаг 3: Конфигурация

**Bot Token:**
```
8579457514:AAEAzcBbCpf4Lq9wj762cKhzzdjEXjf_Zso
```

**Локация развертывания:**
```
✅ Россия (Москва)  - для российских пользователей
или
✅ Нидерланды (Амстердам) - для европейских пользователей
```

### Шаг 4: Переменные окружения

Нажмите **"Добавить переменную окружения"** и добавьте:

| Ключ | Значение |
|------|----------|
| `LOG_CHANNEL_ID` | `-1003626245326` |
| `DISCORD_URL` | `https://discord.com/invite/2H29WNfNa3` |
| `CREATOR_URL` | `https://t.me/pexepo` |
| `SUBMISSION_COOLDOWN_SECONDS` | `90` |

**Не добавляйте TOKEN** - он уже указан в поле "Bot Token"!

### Шаг 5: Репозиторий

**Git URL репозитория:**
```
https://github.com/ваш_username/mrm-bot.git
```

**Ветка:**
```
main
```

**Описание:**
```
Бот для приема работ (эдитов и артов) для канала @etomrm
```

### Шаг 6: Дополнительные настройки

**Использовать домен:**
```
❌ НЕ включайте (бот работает через long polling, не webhook)
```

**Главный файл:**
```
bot.py
```

**Использовать собственный Dockerfile:**
```
❌ НЕ включайте (используем автоматическую сборку)
```

### Шаг 7: Создание

Нажмите **"Создать бота"** и дождитесь деплоя (2-5 минут).

---

## Деплой АДМИН-ПАНЕЛИ на Bothost

### Шаг 1: Создание второго бота

1. Вернитесь в панель Bothost
2. Нажмите **"Создать нового бота"** еще раз

### Шаг 2: Основные настройки

**Название бота:**
```
MRM Admin Panel
```

**Платформа:**
```
✅ Telegram (выбираем, хотя это веб-панель)
```

**Библиотека:**
```
✅ Python
```

**Версия Python:**
```
3.11 (рекомендуется)
```

### Шаг 3: Конфигурация

**Bot Token:**
```
8579457514:AAEAzcBbCpf4Lq9wj762cKhzzdjEXjf_Zso
(тот же токен - панель использует его для скачивания медиа)
```

**Локация развертывания:**
```
✅ Россия (Москва) или Нидерланды (Амстердам)
(выберите ту же, что и для бота)
```

### Шаг 4: Переменные окружения

| Ключ | Значение |
|------|----------|
| `LOG_CHANNEL_ID` | `-1003626245326` |
| `ADMIN_USERNAME` | `admin` |
| `ADMIN_PASSWORD` | `ваш_надежный_пароль` |
| `ADMIN_SECRET_KEY` | `случайная_строка_для_сессий_12345` |
| `PORT` | `5000` |

### Шаг 5: Репозиторий

**Git URL репозитория:**
```
https://github.com/ваш_username/mrm-bot.git
(тот же репозиторий!)
```

**Ветка:**
```
main
```

**Описание:**
```
Админ-панель для управления ботом MRM Community
```

### Шаг 6: Дополнительные настройки

**Использовать домен:**
```
✅ ВКЛЮЧИТЕ! (панель - это веб-сервер)
```

**Главный файл:**
```
admin_panel.py
```

**Использовать собственный Dockerfile:**
```
❌ НЕ включайте
```

### Шаг 7: Создание

Нажмите **"Создать бота"** и дождитесь деплоя.

После деплоя вы получите URL типа: `https://bot1234.bothost.ru`

---

## ⚠️ ВАЖНО: Общая база данных

Поскольку бот и панель на разных контейнерах, у них будут **разные базы данных**.

### Решение: Используйте внешнюю БД

Вам нужно настроить PostgreSQL. Вот как:

### 1. Создайте бесплатную PostgreSQL БД

Используйте один из сервисов:
- **Supabase** (https://supabase.com) - бесплатно, 500 MB
- **Neon** (https://neon.tech) - бесплатно, 3 GB
- **Railway** (https://railway.app) - бесплатно, 1 GB

### 2. Получите DATABASE_URL

После создания БД вы получите строку подключения типа:
```
postgresql://user:password@host:5432/database
```

### 3. Обновите код для PostgreSQL

Создайте файл `database_postgres.py`:

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Создание таблиц
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            total_submissions INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            log_type TEXT,
            user_id BIGINT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS media_submissions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            kind TEXT,
            media_type TEXT,
            file_id TEXT,
            caption TEXT,
            social_link TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    
    conn.commit()
    conn.close()

# Остальные функции аналогично, но с psycopg2 вместо sqlite3
```

### 4. Добавьте переменную DATABASE_URL

В настройках **обоих** ботов на Bothost добавьте:

| Ключ | Значение |
|------|----------|
| `DATABASE_URL` | `postgresql://user:password@host:5432/database` |

### 5. Обновите requirements.txt

Добавьте:
```
psycopg2-binary==2.9.9
```

---

## Альтернативное решение (проще)

### Запустите всё в одном контейнере

Создайте файл `start.sh`:

```bash
#!/bin/bash

# Запускаем бота в фоне
python bot.py &

# Запускаем админ-панель
python admin_panel.py
```

Сделайте его исполняемым:
```bash
chmod +x start.sh
```

Создайте **один** бот на Bothost:
- **Главный файл:** `start.sh`
- **Использовать домен:** ✅ Включено
- Все переменные окружения из обоих ботов

Теперь бот и панель будут в одном контейнере с общей БД!

---

## Проверка работы

### Проверка бота:

1. Откройте бота в Telegram
2. Отправьте `/start`
3. Проверьте, что бот отвечает

### Проверка панели:

1. Откройте URL панели (например: `https://bot1234.bothost.ru`)
2. Войдите с логином/паролем
3. Проверьте, что видны работы

### Просмотр логов:

В панели Bothost:
1. Выберите бота
2. Перейдите в раздел **"Логи"**
3. Смотрите вывод в реальном времени

---

## Решение проблем

### Бот не запускается

1. Проверьте логи в панели Bothost
2. Убедитесь, что все переменные окружения добавлены
3. Проверьте, что `requirements.txt` содержит все зависимости
4. Убедитесь, что токен бота правильный

### Панель не открывается

1. Убедитесь, что включена опция **"Использовать домен"**
2. Проверьте, что `admin_panel.py` указан как главный файл
3. Проверьте логи на наличие ошибок
4. Убедитесь, что `PORT=5000` в переменных окружения

### База данных пустая

1. Если бот и панель на разных контейнерах - используйте PostgreSQL
2. Или используйте решение с `start.sh` для запуска в одном контейнере

---

## Рекомендации

1. **Используйте приватный репозиторий** на GitHub для безопасности
2. **Не храните токены в коде** - только в переменных окружения
3. **Используйте сильный пароль** для админ-панели
4. **Регулярно делайте бэкапы** базы данных
5. **Мониторьте логи** на наличие ошибок

---

## Поддержка

Если возникли проблемы:
- Проверьте логи в панели Bothost
- Убедитесь, что все файлы загружены в репозиторий
- Свяжитесь с поддержкой Bothost: https://t.me/bothostru
- Или с создателем бота: https://t.me/pexepo

---

**Готово! Ваш бот и админ-панель работают на Bothost! 🎉**
