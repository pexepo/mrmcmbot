# 🚀 Гайд по деплою бота на хостинг

## Содержание
1. [Подготовка проекта](#подготовка-проекта)
2. [Деплой на Railway](#деплой-на-railway)
3. [Деплой на Render](#деплой-на-render)
4. [Деплой на VPS (Ubuntu)](#деплой-на-vps-ubuntu)
5. [Настройка переменных окружения](#настройка-переменных-окружения)

---

## Подготовка проекта

### 1. Проверьте файлы проекта

Убедитесь, что у вас есть все необходимые файлы:
```
booot/
├── bot.py                 # Основной файл бота
├── admin_panel.py         # Админ-панель
├── database.py            # Работа с БД
├── requirements.txt       # Зависимости
├── requirements_web.txt   # Зависимости для веб-панели
├── Procfile              # Для Railway/Heroku
├── runtime.txt           # Версия Python
├── templates/            # HTML шаблоны
│   ├── dashboard.html
│   ├── media.html
│   ├── media_detail.html
│   └── ...
├── start.png             # Изображения
├── rules.png
├── send_work.png
├── social_link.png
├── success.png
└── why.mp4
```

### 2. Создайте файл `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# База данных
*.db
*.sqlite
*.sqlite3

# Конфиденциальные данные
.env
bans.json
users.json

# IDE
.vscode/
.idea/
*.swp
*.swo

# Логи
*.log
```

### 3. Обновите `requirements.txt`

```txt
aiogram==3.26.0
```

### 4. Создайте `requirements_web.txt`

```txt
flask==3.0.0
aiogram==3.26.0
```

### 5. Создайте `Procfile`

```
web: python admin_panel.py
worker: python bot.py
```

### 6. Создайте `runtime.txt`

```
python-3.11.9
```

---

## Деплой на Railway

Railway - простой и бесплатный хостинг для начала.

### Шаг 1: Подготовка

1. Зарегистрируйтесь на [Railway.app](https://railway.app)
2. Установите Railway CLI (опционально):
   ```bash
   npm i -g @railway/cli
   ```

### Шаг 2: Создание проекта

1. Перейдите в [Railway Dashboard](https://railway.app/dashboard)
2. Нажмите **"New Project"**
3. Выберите **"Deploy from GitHub repo"** или **"Empty Project"**

### Шаг 3: Загрузка кода

**Вариант A: Через GitHub**
1. Подключите свой GitHub аккаунт
2. Создайте репозиторий и загрузите код
3. Выберите репозиторий в Railway

**Вариант B: Через Railway CLI**
```bash
cd C:\Users\pexep\Downloads\booot
railway login
railway init
railway up
```

### Шаг 4: Настройка переменных окружения

В Railway Dashboard → Variables добавьте:

```env
# Обязательные
TOKEN=ваш_токен_бота
LOG_CHANNEL_ID=-1003626245326
DISCORD_URL=https://discord.com/invite/2H29WNfNa3
CREATOR_URL=https://t.me/pexepo

# Для админ-панели
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ваш_надежный_пароль
ADMIN_SECRET_KEY=случайная_строка_для_сессий

# Опционально
PORT=5000
```

### Шаг 5: Настройка сервисов

Railway автоматически создаст один сервис. Вам нужно создать два:

1. **Бот (Worker)**:
   - Settings → Start Command: `python bot.py`
   - Не назначайте домен

2. **Админ-панель (Web)**:
   - Settings → Start Command: `python admin_panel.py`
   - Generate Domain для доступа к панели

### Шаг 6: Деплой

Railway автоматически задеплоит проект. Проверьте логи:
- Logs → выберите сервис
- Убедитесь, что бот запустился без ошибок

---

## Деплой на Render

Render - альтернатива Railway с бесплатным тарифом.

### Шаг 1: Подготовка

1. Зарегистрируйтесь на [Render.com](https://render.com)
2. Загрузите код на GitHub

### Шаг 2: Создание Web Service (Админ-панель)

1. Dashboard → **New** → **Web Service**
2. Подключите GitHub репозиторий
3. Настройки:
   - **Name**: `mrm-admin-panel`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements_web.txt`
   - **Start Command**: `python admin_panel.py`
   - **Plan**: Free

### Шаг 3: Создание Background Worker (Бот)

1. Dashboard → **New** → **Background Worker**
2. Подключите тот же репозиторий
3. Настройки:
   - **Name**: `mrm-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Plan**: Free

### Шаг 4: Настройка переменных окружения

Для каждого сервиса добавьте переменные (см. раздел "Настройка переменных окружения")

### Шаг 5: Настройка базы данных

Render автоматически создаст файл `bot_data.db`. Для постоянного хранения:

1. Dashboard → **New** → **Disk**
2. Подключите к Background Worker
3. Mount Path: `/opt/render/project/src`

---

## Деплой на VPS (Ubuntu)

Для полного контроля используйте VPS (DigitalOcean, Hetzner, Contabo и т.д.)

### Шаг 1: Подключение к серверу

```bash
ssh root@ваш_ip_адрес
```

### Шаг 2: Установка зависимостей

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Python и pip
apt install python3 python3-pip python3-venv git -y

# Установка Nginx (для админ-панели)
apt install nginx -y

# Установка supervisor (для автозапуска)
apt install supervisor -y
```

### Шаг 3: Загрузка проекта

```bash
# Создание директории
mkdir -p /opt/mrm-bot
cd /opt/mrm-bot

# Клонирование репозитория
git clone https://github.com/ваш_username/ваш_репозиторий.git .

# Или загрузка через SCP
# scp -r C:\Users\pexep\Downloads\booot/* root@ваш_ip:/opt/mrm-bot/
```

### Шаг 4: Настройка виртуального окружения

```bash
cd /opt/mrm-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_web.txt
```

### Шаг 5: Создание .env файла

```bash
nano /opt/mrm-bot/.env
```

Добавьте:
```env
TOKEN=ваш_токен_бота
LOG_CHANNEL_ID=-1003626245326
DISCORD_URL=https://discord.com/invite/2H29WNfNa3
CREATOR_URL=https://t.me/pexepo
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ваш_надежный_пароль
ADMIN_SECRET_KEY=случайная_строка
PORT=5000
```

### Шаг 6: Настройка Supervisor (автозапуск)

Создайте конфиг для бота:
```bash
nano /etc/supervisor/conf.d/mrm-bot.conf
```

```ini
[program:mrm-bot]
command=/opt/mrm-bot/venv/bin/python /opt/mrm-bot/bot.py
directory=/opt/mrm-bot
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/mrm-bot.err.log
stdout_logfile=/var/log/mrm-bot.out.log
environment=PATH="/opt/mrm-bot/venv/bin"
```

Создайте конфиг для админ-панели:
```bash
nano /etc/supervisor/conf.d/mrm-admin.conf
```

```ini
[program:mrm-admin]
command=/opt/mrm-bot/venv/bin/python /opt/mrm-bot/admin_panel.py
directory=/opt/mrm-bot
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/mrm-admin.err.log
stdout_logfile=/var/log/mrm-admin.out.log
environment=PATH="/opt/mrm-bot/venv/bin"
```

Перезапустите Supervisor:
```bash
supervisorctl reread
supervisorctl update
supervisorctl start mrm-bot
supervisorctl start mrm-admin
```

### Шаг 7: Настройка Nginx (для админ-панели)

```bash
nano /etc/nginx/sites-available/mrm-admin
```

```nginx
server {
    listen 80;
    server_name ваш_домен.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте конфиг:
```bash
ln -s /etc/nginx/sites-available/mrm-admin /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Шаг 8: Установка SSL (опционально)

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d ваш_домен.com
```

### Шаг 9: Проверка работы

```bash
# Проверка статуса
supervisorctl status

# Просмотр логов
tail -f /var/log/mrm-bot.out.log
tail -f /var/log/mrm-admin.out.log

# Перезапуск сервисов
supervisorctl restart mrm-bot
supervisorctl restart mrm-admin
```

---

## Настройка переменных окружения

### Обязательные переменные

| Переменная | Описание | Пример |
|------------|----------|--------|
| `TOKEN` | Токен бота от @BotFather | `8579457514:AAEAzcBbCpf4...` |
| `LOG_CHANNEL_ID` | ID канала для логов | `-1003626245326` |
| `DISCORD_URL` | Ссылка на Discord | `https://discord.com/invite/...` |
| `CREATOR_URL` | Ссылка на создателя | `https://t.me/pexepo` |

### Переменные для админ-панели

| Переменная | Описание | Пример |
|------------|----------|--------|
| `ADMIN_USERNAME` | Логин админа | `admin` |
| `ADMIN_PASSWORD` | Пароль админа | `SecurePass123!` |
| `ADMIN_SECRET_KEY` | Секретный ключ для сессий | `random_string_here` |
| `PORT` | Порт для веб-панели | `5000` |

### Как получить LOG_CHANNEL_ID

1. Добавьте бота в канал как администратора
2. Отправьте сообщение в канал
3. Перейдите по ссылке:
   ```
   https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates
   ```
4. Найдите `"chat":{"id":-1003626245326}` - это и есть ID канала

---

## Полезные команды

### Обновление кода на сервере

```bash
cd /opt/mrm-bot
git pull
supervisorctl restart mrm-bot
supervisorctl restart mrm-admin
```

### Просмотр логов

```bash
# Логи бота
tail -f /var/log/mrm-bot.out.log

# Логи админ-панели
tail -f /var/log/mrm-admin.out.log

# Логи Nginx
tail -f /var/log/nginx/error.log
```

### Резервное копирование базы данных

```bash
# Создание бэкапа
cp /opt/mrm-bot/bot_data.db /opt/mrm-bot/backups/bot_data_$(date +%Y%m%d).db

# Автоматический бэкап (добавьте в crontab)
crontab -e
# Добавьте строку:
0 3 * * * cp /opt/mrm-bot/bot_data.db /opt/mrm-bot/backups/bot_data_$(date +\%Y\%m\%d).db
```

---

## Решение проблем

### Бот не запускается

1. Проверьте логи: `tail -f /var/log/mrm-bot.err.log`
2. Проверьте токен бота
3. Убедитесь, что все зависимости установлены
4. Проверьте права на файлы: `chmod +x bot.py`

### Админ-панель недоступна

1. Проверьте, запущен ли сервис: `supervisorctl status mrm-admin`
2. Проверьте порт: `netstat -tulpn | grep 5000`
3. Проверьте Nginx: `nginx -t`
4. Проверьте логи: `tail -f /var/log/mrm-admin.err.log`

### База данных не сохраняется

1. Проверьте права на директорию: `chmod 755 /opt/mrm-bot`
2. Убедитесь, что диск подключен (для Render)
3. Проверьте наличие файла: `ls -la /opt/mrm-bot/*.db`

---

## Рекомендации по безопасности

1. **Используйте сильные пароли** для админ-панели
2. **Настройте firewall**:
   ```bash
   ufw allow 22/tcp
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```
3. **Регулярно обновляйте систему**:
   ```bash
   apt update && apt upgrade -y
   ```
4. **Используйте SSL** для админ-панели
5. **Ограничьте доступ** к админ-панели по IP (опционально)

---

## Поддержка

Если возникли проблемы:
- Проверьте логи
- Убедитесь, что все переменные окружения настроены
- Проверьте, что бот добавлен в лог-канал как администратор
- Свяжитесь с создателем: https://t.me/pexepo

---

**Готово! Ваш бот теперь работает на хостинге 🎉**
