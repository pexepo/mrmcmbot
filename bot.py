import asyncio
import html
import json
import logging
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    ErrorEvent,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    User,
)


# Конфиг. Значения можно переопределить через переменные окружения.
TOKEN = os.getenv("BOT_TOKEN", "8579457514:AAEAzcBbCpf4Lq9wj762cKhzzdjEXjf_Zso").strip()
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1003626245326"))
DISCORD_URL = os.getenv("DISCORD_URL", "https://discord.com/invite/2H29WNfNa3").strip()
CREATOR_URL = os.getenv("CREATOR_URL", "https://t.me/pexepo").strip()
SUBMISSION_COOLDOWN_SECONDS = int(os.getenv("SUBMISSION_COOLDOWN_SECONDS", "90"))

def parse_admin_ids(raw_value: str | None) -> set[int]:
    value = raw_value or "1784522503"
    result: set[int] = set()
    for chunk in value.split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            result.add(int(chunk))
    return result


ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS"))

BASE_DIR = Path(__file__).resolve().parent
BANS_FILE = BASE_DIR / "bans.json"
USERS_FILE = BASE_DIR / "users.json"


def resolve_image(stem: str) -> Path:
    png_path = BASE_DIR / f"{stem}.png"
    if png_path.exists():
        return png_path
    return BASE_DIR / f"{stem}.jpg"


def resolve_optional_image(stem: str, fallback: Path) -> Path:
    png_path = BASE_DIR / f"{stem}.png"
    if png_path.exists():
        return png_path

    jpg_path = BASE_DIR / f"{stem}.jpg"
    if jpg_path.exists():
        return jpg_path

    return fallback


START_IMAGE = resolve_image("start")
SEND_WORK_IMAGE = resolve_image("send_work")
RULES_IMAGE = BASE_DIR / "rules.png"
SUCCESS_IMAGE = BASE_DIR / "success.png"
DISCORD_IMAGE = resolve_optional_image("discord", START_IMAGE)
if not SUCCESS_IMAGE.exists():
    SUCCESS_IMAGE = SEND_WORK_IMAGE

SCREEN_IMAGES = (
    START_IMAGE,
    RULES_IMAGE,
    SEND_WORK_IMAGE,
    SUCCESS_IMAGE,
)


def button_text(label: str, fallback_emoji: str, emoji_key: str) -> str:
    return f"{fallback_emoji} {label}".strip()


def button_with_icon(
    label: str,
    fallback_emoji: str,
    emoji_key: str,
    icon_custom_emoji_id: str | None = None,
    style: str | None = None,
) -> KeyboardButton:
    return KeyboardButton(
        text=button_text(label, fallback_emoji, emoji_key),
        icon_custom_emoji_id=icon_custom_emoji_id,
        style=style,
    )


def inline_button_with_icon(
    label: str,
    fallback_emoji: str,
    emoji_key: str,
    *,
    callback_data: str | None = None,
    url: str | None = None,
    icon_custom_emoji_id: str | None = None,
    style: str | None = None,
) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=button_text(label, fallback_emoji, emoji_key),
        callback_data=callback_data,
        url=url,
        icon_custom_emoji_id=icon_custom_emoji_id,
        style=style,
    )


BTN_SEND_EDIT = "Отправить эдит"
BTN_SEND_ART = "Отправить арт"
BTN_DISCORD = "Discord сервер"
BTN_CREATOR = "Связь с создателем"
BTN_ACCEPT = "Согласиться"
BTN_DECLINE = "Отказаться"
BTN_BACK = "Назад"
BTN_OPEN = "Перейти"
BTN_MAIN_MENU = "Главное меню"
BTN_RETRY_SEND = "Отправка работы"

ICON_SEND_EDIT = ""
ICON_SEND_ART = ""
ICON_DISCORD = ""
ICON_CREATOR = ""
ICON_ACCEPT = ""
ICON_DECLINE = ""
ICON_BACK = "↩️"

KIND_LABELS = {
    "edit": "эдит",
    "art": "арт",
}

RULES = {
    "edit": {
        "image": RULES_IMAGE,
        "caption": (
            "<tg-emoji emoji-id=\"5440660757194744323\">‼</tg-emoji><b>ПЕРЕД ТЕМ КАК КИДАТЬ ЭДИТ ОЗНАКОМЬСЯ С ПРАВИЛАМИ</b>\n\n"
            "1. Принимаются только ваши собственные работы.<tg-emoji emoji-id=\"5244555952073499173\">❗</tg-emoji>\n"
            "2. NSFL строго нет, на пост NSFW эдита шанс мизерный.<tg-emoji emoji-id=\"5267395415627567516\">💕</tg-emoji>\n"
            "3. Убедитесь что эдит не усыпан пикселями, низким битрейтом.<tg-emoji emoji-id=\"6001305528653844732\">❕</tg-emoji>\n"
            "4. Музыка, клипы, стиль абсолютно неважны.\n"
            "5. Эдит может как использоваться для постинга в канал, так и может не использоваться.\n"
            "6. Обязательно к эдиту приложите ссылку или юзернейм на одну из своих соцсеток(указать какую), в которой должно быть: если 1000+ - ссылка на телеграм канал машрум (@etomrm), меньше 1000 - приставка .mrm в вашем собственном юзернейме.\n\n"
            "Нажимая <b>Согласиться</b> вы соглашаетесь с данными правилами. В случае несоблюдения одного из правил предусмотрен бан, который спокойно можно обжаловать."
        ),
    },
    "art": {
        "image": RULES_IMAGE,
        "caption": (
            "<tg-emoji emoji-id=\"5440660757194744323\">‼</tg-emoji> <b>ПЕРЕД ТЕМ КАК КИДАТЬ АРТ ОЗНАКОМЬСЯ С ПРАВИЛАМИ</b>\n\n"
            "1. Принимаются только ваши собственные работы.<tg-emoji emoji-id=\"5244555952073499173\">❗</tg-emoji>\n"
            "2. NSFL строго нет, на пост NSFW арта шанс мизерный.<tg-emoji emoji-id=\"5267395415627567516\">💕</tg-emoji>\n"
            "3. Убедитесь что арт в хорошем качестве. Файлы разрешены. Арт будет перешлен в ужатом качестве, а исходое качество будет отправлено в комментарии.\n"
            "4. Эдит может как использоваться для постинга в канал, так и может не использоваться.\n"
            "5. Обязательно к арту приложите ссылку или юзернейм на одну из своих соцсеток(указать какую), в которой должно быть: 1000+ - ссылка на телеграм канал машрум (@etomrm), меньше 1000 - приставка .mrm в вашем собственном юзернейме.\n\n"
            "Нажимая <b>Согласиться</b> вы соглашаетесь с данными правилами. В случае несоблюдения одного из правил предусмотрен бан, который спокойно можно обжаловать."
        ),
    },
}

INFO_SCREENS = {
    "discord": {
        "image": DISCORD_IMAGE,
        "icon": ICON_DISCORD,
        "title": "Discord сервер",
        "description": "Ниже есть кликабельная ссылка на дискорд сервер нашего сообщества.",
        "url": DISCORD_URL,
    },
    "creator": {
        "image": START_IMAGE,
        "icon": ICON_CREATOR,
        "title": "Связь с создателем",
        "description": "Есть вопросы по предложке? Хотите уточнить или обжаловать причину бана? Бот не работает? Вот моя элэс.",
        "url": CREATOR_URL,
    },
}

START_CAPTION = (
    "<tg-emoji emoji-id=\"5244682331486187125\">👋</tg-emoji> <b>Приветствую!</b>\n\n"
    "Это предложка для канала @etomrm. Здесь вы можете отправить свой потрясный эдит или крутой арт, который мы заметим и выложим в канал, если работа действительно достойная\n"
    "Бот сначала покажет правила, затем попросит прислать работу одним сообщением.<tg-emoji emoji-id=\"5244726380670773077\">⚡</tg-emoji>"
)

BANNED_CAPTION = (
    "🚫 <b>Доступ к предложке закрыт.</b>\n\n"
    "Если это ошибка, свяжитесь с создателем бота."
)

NO_ADMIN_CAPTION = (
    "🚫 <b>Недостаточно прав</b>\n\n"
    "Эта команда доступна только администраторам бота."
)

SEND_WORK_CAPTION = (
    "<tg-emoji emoji-id=\"5253742260054409879\">📨</tg-emoji> <b>Отправляйте вашу работу</b>\n\n"
    "Пришлите её одним сообщением в этот чат. Не забудьте подпись\n"
    "Поддерживаются фото, видео, анимации и файлы."
)

SUCCESS_CAPTION = (
    "<tg-emoji emoji-id=\"5206607081334906820\">✔</tg-emoji> <b>Ваша работа была успешно отправлена!</b>\n\n"
    "Она уже улетела к нам и будет рассмотрена как можно скорее <tg-emoji emoji-id=\"5287598581010691474\">❤</tg-emoji>"
)

SUCCESS_BACK_CAPTION = (
    SUCCESS_CAPTION
    + "\n\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u00ab\u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e\u00bb, "
    + "\u0447\u0442\u043e\u0431\u044b \u0432\u0435\u0440\u043d\u0443\u0442\u044c\u0441\u044f \u0432 \u043c\u0435\u043d\u044e."
)

INVALID_WORK_CAPTION = (
    "<tg-emoji emoji-id=\"5447644880824181073\">⚠</tg-emoji> <b>Нужна сама работа</b>\n\n"
    "Отправьте фото, видео, анимацию или документ одним сообщением."
)

UNKNOWN_COMMAND_CAPTION = (
    "ℹ️ <b>Команда не распознана</b>\n\n"
    "Используйте кнопки в меню ниже."
)

EDIT_INVALID_CAPTION = (
    "⚠️ <b>Для эдита нужно видео или файл</b>\n\n"
    "Фото как готовый эдит не принимается. "
    "Отправьте видео, GIF/анимацию или файл."
)

ART_INVALID_CAPTION = (
    "⚠️ <b>Для арта нужно фото или файл</b>\n\n"
    "Видео как готовый арт не принимается. "
    "Отправьте фото или файл."
)

LOGGER = logging.getLogger("suggestion_bot")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


class Suggestion(StatesGroup):
    reviewing_rules = State()
    waiting_for_work = State()


def load_registry(path: Path, root_key: str) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        LOGGER.exception("Не удалось прочитать %s", path.name)
        return {}

    data = payload.get(root_key, {})
    result: dict[int, dict[str, Any]] = {}
    for raw_user_id, metadata in data.items():
        if str(raw_user_id).isdigit() and isinstance(metadata, dict):
            result[int(raw_user_id)] = metadata
    return result


def save_registry(path: Path, root_key: str, data: dict[int, dict[str, Any]]) -> None:
    payload = {
        root_key: {
            str(user_id): metadata
            for user_id, metadata in sorted(data.items(), key=lambda item: item[0])
        }
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


ban_registry: dict[int, dict[str, Any]] = load_registry(BANS_FILE, "banned_users")
user_registry: dict[int, dict[str, Any]] = load_registry(USERS_FILE, "users")
last_submission_at: dict[int, float] = {}


def save_bans() -> None:
    save_registry(BANS_FILE, "banned_users", ban_registry)


def save_users() -> None:
    save_registry(USERS_FILE, "users", user_registry)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_banned(user_id: int) -> bool:
    return user_id in ban_registry


def photo(image_path: Path) -> FSInputFile:
    return FSInputFile(str(image_path))


def normalize_text(text: str | None) -> str:
    return " ".join((text or "").casefold().split())


ACTION_ALIASES = {
    normalize_text(BTN_SEND_EDIT): "send_edit",
    normalize_text(f"{ICON_SEND_EDIT} {BTN_SEND_EDIT}"): "send_edit",
    normalize_text("отправить эдит"): "send_edit",
    normalize_text("эдит"): "send_edit",
    normalize_text(BTN_SEND_ART): "send_art",
    normalize_text(f"{ICON_SEND_ART} {BTN_SEND_ART}"): "send_art",
    normalize_text("отправить арт"): "send_art",
    normalize_text("арт"): "send_art",
    normalize_text(BTN_DISCORD): "discord",
    normalize_text(f"{ICON_DISCORD} {BTN_DISCORD}"): "discord",
    normalize_text("discord сервер"): "discord",
    normalize_text("discord"): "discord",
    normalize_text(BTN_CREATOR): "creator",
    normalize_text(f"{ICON_CREATOR} {BTN_CREATOR}"): "creator",
    normalize_text("связь с создателем"): "creator",
    normalize_text("создатель"): "creator",
    normalize_text(BTN_ACCEPT): "accept",
    normalize_text(f"{ICON_ACCEPT} {BTN_ACCEPT}"): "accept",
    normalize_text("согласиться"): "accept",
    normalize_text("согласен"): "accept",
    normalize_text(BTN_DECLINE): "decline",
    normalize_text(f"{ICON_DECLINE} {BTN_DECLINE}"): "decline",
    normalize_text("отказаться"): "decline",
    normalize_text("отказ"): "decline",
    normalize_text(BTN_BACK): "back",
    normalize_text(f"{ICON_BACK} {BTN_BACK}"): "back",
    normalize_text(BTN_MAIN_MENU): "back",
    normalize_text(f"{ICON_BACK} {BTN_MAIN_MENU}"): "back",
    normalize_text("назад"): "back",
    normalize_text("главное меню"): "back",
}


def resolve_action(text: str | None) -> str | None:
    return ACTION_ALIASES.get(normalize_text(text))


def build_reply_keyboard(
    rows: list[list[tuple[str, str, str, str | None, str | None]]],
    placeholder: str,
) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                button_with_icon(
                    label=label,
                    fallback_emoji=fallback_emoji,
                    emoji_key=emoji_key,
                    icon_custom_emoji_id=custom_emoji_id,
                    style=style,
                )
                for label, fallback_emoji, emoji_key, custom_emoji_id, style in row
            ]
            for row in rows
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=placeholder,
    )


def persistent_menu() -> ReplyKeyboardMarkup:
    return build_reply_keyboard(
        [
            [
                (BTN_SEND_EDIT, ICON_SEND_EDIT, "send_edit", "5190674036861992770", "primary"),
                (BTN_SEND_ART, ICON_SEND_ART, "send_art", "5409109841538994759", "primary"),
            ],
            [
                (BTN_ACCEPT, ICON_ACCEPT, "accept", "5289671946408043028", "success"),
                (BTN_DECLINE, ICON_DECLINE, "decline", "5289576280306493734", "danger"),
            ],
            [
                (BTN_DISCORD, ICON_DISCORD, "discord", "5325612636467903082", "default"),
                (BTN_CREATOR, ICON_CREATOR, "creator", "5330237710655306682", "default"),
            ],
            [
                (BTN_BACK, ICON_BACK, "back", None, "default"),
            ],
        ],
        "Выберите действие",
    )


def main_menu() -> ReplyKeyboardMarkup:
    return build_reply_keyboard(
        [
            [
                (BTN_SEND_EDIT, ICON_SEND_EDIT, "send_edit", "5190674036861992770", "primary"),
                (BTN_SEND_ART, ICON_SEND_ART, "send_art", "5409109841538994759", "primary"),
            ],
            [
                (BTN_DISCORD, ICON_DISCORD, "discord", "5325612636467903082", "default"),
                (BTN_CREATOR, ICON_CREATOR, "creator", "5330237710655306682", "default"),
            ],
        ],
        "Выберите действие",
    )


def rules_menu() -> ReplyKeyboardMarkup:
    return build_reply_keyboard(
        [[
            (BTN_ACCEPT, ICON_ACCEPT, "accept", "5289671946408043028", "success"),
            (BTN_DECLINE, ICON_DECLINE, "decline", "5289576280306493734", "danger"),
        ]],
        "Примите или отклоните правила",
    )


def info_menu() -> ReplyKeyboardMarkup:
    return build_reply_keyboard(
        [[(BTN_BACK, ICON_BACK, "back", None, "default")]],
        "Вернуться назад",
    )


def send_work_menu() -> ReplyKeyboardMarkup:
    return build_reply_keyboard(
        [[(BTN_BACK, ICON_BACK, "back", None, "default")]],
        "Отправьте работу или вернитесь назад",
    )


def banned_menu() -> ReplyKeyboardMarkup:
    return build_reply_keyboard(
        [[(BTN_CREATOR, ICON_CREATOR, "creator", "5771449289972650710", "default")]],
        "Связаться с создателем",
    )


def inline_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    BTN_SEND_EDIT,
                    ICON_SEND_EDIT,
                    "send_edit",
                    callback_data="rules:edit",
                    icon_custom_emoji_id="5190674036861992770",
                    style="primary",
                ),
                inline_button_with_icon(
                    BTN_SEND_ART,
                    ICON_SEND_ART,
                    "send_art",
                    callback_data="rules:art",
                    icon_custom_emoji_id="6028435952299413210",
                    style="primary",
                ),
            ],
            [
                inline_button_with_icon(
                    BTN_DISCORD,
                    ICON_DISCORD,
                    "discord",
                    url=DISCORD_URL,
                    icon_custom_emoji_id="5771449289972650710",
                    style="default",
                )
            ],
            [
                inline_button_with_icon(
                    BTN_CREATOR,
                    ICON_CREATOR,
                    "creator",
                    callback_data="info:creator",
                    icon_custom_emoji_id="5771449289972650710",
                    style="default",
                )
            ],
        ]
    )


def inline_rules_menu(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    BTN_ACCEPT,
                    ICON_ACCEPT,
                    "accept",
                    callback_data=f"accept:{kind}",
                    icon_custom_emoji_id="5289671946408043028",
                    style="success",
                ),
                inline_button_with_icon(
                    BTN_DECLINE,
                    ICON_DECLINE,
                    "decline",
                    callback_data="start",
                    icon_custom_emoji_id="5289576280306493734",
                    style="danger",
                ),
            ]
        ]
    )


def inline_info_menu(kind: str) -> InlineKeyboardMarkup:
    info = INFO_SCREENS[kind]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    BTN_OPEN,
                    "",
                    "open",
                    url=info["url"],
                    style="primary",
                )
            ],
            [
                inline_button_with_icon(
                    BTN_BACK,
                    ICON_BACK,
                    "back",
                    callback_data="start",
                    style="default",
                )
            ],
        ]
    )


def inline_send_work_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    BTN_BACK,
                    ICON_BACK,
                    "back",
                    callback_data="start",
                    style="default",
                )
            ]
        ]
    )


def inline_failure_menu(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    BTN_RETRY_SEND,
                    "📨",
                    "send",
                    callback_data=f"retry:{kind}",
                    icon_custom_emoji_id="6028435952299413210",
                    style="primary",
                )
            ]
        ]
    )


def inline_banned_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    BTN_CREATOR,
                    ICON_CREATOR,
                    "creator",
                    url=CREATOR_URL,
                    icon_custom_emoji_id="5771449289972650710",
                    style="default",
                )
            ]
        ]
    )


def success_menu() -> ReplyKeyboardMarkup:
    return build_reply_keyboard(
        [[(BTN_MAIN_MENU, ICON_BACK, "back", None, "success")]],
        "Вернуться в меню",
    )


def inline_success_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    BTN_MAIN_MENU,
                    ICON_BACK,
                    "back",
                    callback_data="start",
                    style="success",
                )
            ]
        ]
    )


def escape_text(value: Any) -> str:
    if value is None:
        return "—"
    return html.escape(str(value))


def trim_caption(text: str, limit: int = 1000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def format_timestamp(timestamp: float | None = None) -> str:
    value = timestamp if timestamp is not None else time.time()
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def remember_user(user: User | None) -> bool:
    if not user:
        return False

    is_new_user = user.id not in user_registry

    user_registry[user.id] = {
        "username": user.username or "",
        "full_name": user.full_name or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "language_code": user.language_code or "",
        "last_seen": format_timestamp(),
    }

    try:
        save_users()
    except OSError:
        LOGGER.exception("Не удалось сохранить users.json")


    return is_new_user


async def register_user_activity(user: User | None) -> None:
    if user and remember_user(user):
        await log_to_channel(build_new_user_log(user))


def get_user_profile(user_id: int) -> dict[str, Any]:
    return user_registry.get(user_id, {})


def format_user_card(user_id: int, live_user: User | None = None) -> str:
    profile = get_user_profile(user_id)

    username = (live_user.username if live_user else "") or profile.get("username") or ""
    full_name = (live_user.full_name if live_user else "") or profile.get("full_name") or ""
    language_code = (live_user.language_code if live_user else "") or profile.get("language_code") or ""

    mention_label = escape_text(full_name or f"Пользователь {user_id}")
    lines = [
        f'Пользователь: <a href="tg://user?id={user_id}">{mention_label}</a>',
        f"ID: <code>{user_id}</code>",
    ]

    if username:
        lines.append(f"Username: <code>@{escape_text(username)}</code>")
    if full_name:
        lines.append(f"Имя: {escape_text(full_name)}")
    if language_code:
        lines.append(f"Язык: <code>{escape_text(language_code)}</code>")

    last_seen = profile.get("last_seen")
    if last_seen:
        lines.append(f"Последняя активность: <code>{escape_text(last_seen)}</code>")

    return "\n".join(lines)


def format_user_line(user_id: int) -> str:
    profile = get_user_profile(user_id)
    parts = [f"<code>{user_id}</code>"]

    username = profile.get("username")
    full_name = profile.get("full_name")
    if username:
        parts.append(f"@{escape_text(username)}")
    if full_name:
        parts.append(escape_text(full_name))

    return " | ".join(parts)


def build_info_caption(kind: str) -> str:
    data = INFO_SCREENS[kind]
    return (
        f'{data["icon"]} <b>{escape_text(data["title"])}</b>\n\n'
        f'{escape_text(data["description"])}'
    )


def build_submission_log(message: Message, kind: str) -> str:
    user = message.from_user
    text_part = message.caption or message.text or ""
    preview = escape_text(text_part[:400]) if text_part else "—"

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 <b>Новая работа от</b>\n\n"
        f"👤 <b>Отправил:</b>\n"
        f"{format_user_card(user.id, user)}\n\n"
        f"📂 <b>Отправлен</b> {escape_text(KIND_LABELS.get(kind, kind))}\n"
        f"📎 <b>Файл формата:</b> <code>{escape_text(message.content_type)}</code>\n"
        f"💬 <b>Текст/подпись:</b> {preview}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


def build_new_user_log(user: User) -> str:
    return (
        "👋 <b>Новый пользователь бота</b>\n"
        f"{format_user_card(user.id, user)}"
    )


def get_allowed_content_types(kind: str) -> set[str]:
    if kind == "edit":
        return {"video", "animation", "document"}
    if kind == "art":
        return {"photo", "document"}
    return {"photo", "video", "animation", "document"}


def get_invalid_submission_caption(kind: str) -> str:
    if kind == "edit":
        return EDIT_INVALID_CAPTION
    if kind == "art":
        return ART_INVALID_CAPTION
    return INVALID_WORK_CAPTION


async def sync_reply_keyboard(
    chat_id: int,
    keyboard: ReplyKeyboardMarkup | None = None,
    helper_text: str = "Главное меню",
) -> int | None:
    # Не отправляем лишние сообщения для удаления клавиатуры
    # Клавиатура будет удалена автоматически при отправке следующего сообщения с ReplyKeyboardRemove
    return None


async def send_photo_screen(
    message: Message,
    image_path: Path,
    caption: str,
    inline_keyboard: InlineKeyboardMarkup | None = None,
    reply_keyboard: ReplyKeyboardMarkup | None = None,
    helper_text: str = "Главное меню",
) -> None:
    # Если нужно показать inline кнопки (нет reply клавиатуры)
    if reply_keyboard is None and inline_keyboard is not None:
        # Сначала убираем reply клавиатуру
        remove_msg = await message.answer(
            "⏳",
            reply_markup=ReplyKeyboardRemove(),
        )
        
        # Отправляем фото с inline кнопками
        new_msg = await message.answer_photo(
            photo(image_path),
            caption=trim_caption(caption),
            reply_markup=inline_keyboard,
        )
        
        # Ждем 1 секунду перед удалением старых сообщений
        await asyncio.sleep(1)
        
        # Удаляем все предыдущие сообщения, кроме последних 3
        for i in range(4, 30):  # Начинаем с 4, чтобы оставить последние 3 сообщения
            try:
                await bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=message.message_id - i
                )
            except Exception:
                pass  # Игнорируем ошибки, если сообщение не найдено
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except Exception:
            LOGGER.debug("Не удалось удалить сообщение пользователя")
        
        # Удаляем сообщение с песочными часами
        try:
            await remove_msg.delete()
        except Exception:
            LOGGER.debug("Не удалось удалить сообщение с ReplyKeyboardRemove")
    else:
        # Если есть reply клавиатура или нет кнопок вообще
        photo_reply_markup = reply_keyboard if reply_keyboard is not None else ReplyKeyboardRemove()
        await message.answer_photo(
            photo(image_path),
            caption=trim_caption(caption),
            reply_markup=photo_reply_markup,
        )


async def send_callback_screen(
    callback: CallbackQuery,
    image_path: Path,
    caption: str,
    inline_keyboard: InlineKeyboardMarkup | None = None,
    reply_keyboard: ReplyKeyboardMarkup | None = None,
    helper_text: str = "Главное меню",
) -> None:
    chat_id = callback.message.chat.id if callback.message else callback.from_user.id
    old_message_id = callback.message.message_id if callback.message else None

    # Если нужно показать inline кнопки (нет reply клавиатуры)
    if reply_keyboard is None and inline_keyboard is not None:
        # Сначала убираем reply клавиатуру
        remove_msg = await bot.send_message(
            chat_id=chat_id,
            text="⏳",
            reply_markup=ReplyKeyboardRemove(),
        )
        
        # Затем отправляем фото с inline кнопками
        await bot.send_photo(
            chat_id=chat_id,
            photo=photo(image_path),
            caption=trim_caption(caption),
            reply_markup=inline_keyboard,
        )
        
        # Удаляем предыдущее сообщение (главное меню или другое)
        if old_message_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=old_message_id)
            except Exception:
                LOGGER.debug("Не удалось удалить старое сообщение после callback")
        
        # Удаляем сообщение с песочными часами
        try:
            await bot.delete_message(chat_id=chat_id, message_id=remove_msg.message_id)
        except Exception:
            LOGGER.debug("Не удалось удалить сообщение с ReplyKeyboardRemove")
    else:
        # Удаляем предыдущее сообщение сразу
        if callback.message:
            try:
                await callback.message.delete()
            except Exception:
                LOGGER.debug("Не удалось удалить старое сообщение после callback")
        
        # Если есть reply клавиатура или нет кнопок вообще
        photo_reply_markup = reply_keyboard if reply_keyboard is not None else ReplyKeyboardRemove()
        await bot.send_photo(
            chat_id=chat_id,
            photo=photo(image_path),
            caption=trim_caption(caption),
            reply_markup=photo_reply_markup,
        )

    await callback.answer()


async def show_screen(
    target: Message | CallbackQuery,
    image_path: Path,
    caption: str,
    *,
    inline_keyboard: InlineKeyboardMarkup | None = None,
    reply_keyboard: ReplyKeyboardMarkup | None = None,
    helper_text: str = "Главное меню",
) -> None:
    if isinstance(target, Message):
        await send_photo_screen(
            target,
            image_path,
            caption,
            inline_keyboard=inline_keyboard,
            reply_keyboard=reply_keyboard,
            helper_text=helper_text,
        )
    else:
        await send_callback_screen(
            target,
            image_path,
            caption,
            inline_keyboard=inline_keyboard,
            reply_keyboard=reply_keyboard,
            helper_text=helper_text,
        )


async def show_start_screen(target: Message | CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_screen(
        target,
        START_IMAGE,
        START_CAPTION,
        reply_keyboard=main_menu(),
        helper_text="Главное меню",
    )


async def show_banned_screen(target: Message | CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_screen(
        target,
        START_IMAGE,
        BANNED_CAPTION,
        reply_keyboard=banned_menu(),
        helper_text="Доступ ограничен",
    )


async def show_info_screen(target: Message | CallbackQuery, state: FSMContext, kind: str) -> None:
    await state.clear()
    await show_screen(
        target,
        INFO_SCREENS[kind]["image"],
        build_info_caption(kind),
        inline_keyboard=inline_info_menu(kind),
        reply_keyboard=None,
    )


async def show_rules_screen(target: Message | CallbackQuery, state: FSMContext, kind: str) -> None:
    await state.set_state(Suggestion.reviewing_rules)
    await state.update_data(kind=kind)
    await show_screen(
        target,
        RULES[kind]["image"],
        RULES[kind]["caption"],
        inline_keyboard=inline_rules_menu(kind),
        reply_keyboard=None,
    )


async def show_send_work_screen(target: Message | CallbackQuery, state: FSMContext, kind: str) -> None:
    await state.set_state(Suggestion.waiting_for_work)
    await state.update_data(kind=kind)
    await show_screen(
        target,
        SEND_WORK_IMAGE,
        SEND_WORK_CAPTION,
        reply_keyboard=send_work_menu(),
        helper_text="Отправка работы",
    )


async def show_success_screen(target: Message | CallbackQuery) -> None:
    await show_screen(
        target,
        SUCCESS_IMAGE,
        SUCCESS_BACK_CAPTION,
        inline_keyboard=inline_success_menu(),
        reply_keyboard=None,
    )


async def show_failure_screen(
    target: Message | CallbackQuery,
    state: FSMContext,
    kind: str,
    caption: str,
    *,
    image_path: Path = SEND_WORK_IMAGE,
) -> None:
    await state.set_state(Suggestion.waiting_for_work)
    await state.update_data(kind=kind)
    await show_screen(
        target,
        image_path,
        caption,
        inline_keyboard=inline_failure_menu(kind),
        reply_keyboard=None,
    )


async def ensure_allowed_message(message: Message, state: FSMContext) -> bool:
    await register_user_activity(message.from_user)
    if is_banned(message.from_user.id):
        await show_banned_screen(message, state)
        return False
    return True


async def ensure_allowed_callback(callback: CallbackQuery, state: FSMContext) -> bool:
    await register_user_activity(callback.from_user)
    if is_banned(callback.from_user.id):
        await show_banned_screen(callback, state)
        return False
    return True


async def log_to_channel(text: str) -> None:
    try:
        await bot.send_message(LOG_CHANNEL_ID, text)
    except Exception:
        LOGGER.exception("Не удалось отправить лог в канал")


def validate_assets() -> None:
    missing = [path.name for path in SCREEN_IMAGES if not path.exists()]
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(f"Не найдены файлы изображений: {joined}")


async def set_bot_commands() -> None:
    commands = [
        BotCommand(command="start", description="Открыть главное меню"),
        BotCommand(command="menu", description="Вернуться в меню"),
    ]
    await bot.set_my_commands(commands)


@dp.message(CommandStart())
@dp.message(Command("menu"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return
    
    # Проверяем текущее состояние
    current_state = await state.get_state()
    
    # Если пользователь в процессе (не в главном меню), игнорируем команду
    if current_state is not None:
        # Отправляем уведомление, что команда недоступна
        await message.answer(
            "⚠️ Команды /start и /menu недоступны во время работы с ботом.\n"
            "Используйте кнопки для навигации.",
        )
        return
    
    await show_start_screen(message, state)


@dp.message(Command("ban"))
async def ban_user(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    if not is_admin(message.from_user.id):
        await send_photo_screen(
            message,
            START_IMAGE,
            NO_ADMIN_CAPTION,
            inline_keyboard=inline_main_menu(),
            reply_keyboard=main_menu(),
        )
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        await send_photo_screen(
            message,
            START_IMAGE,
            "ℹ️ <b>Использование</b>\n\n<code>/ban user_id причина</code>",
            inline_keyboard=inline_main_menu(),
            reply_keyboard=main_menu(),
        )
        return

    target_id = int(parts[1])
    reason = parts[2].strip() if len(parts) > 2 else "без причины"
    ban_registry[target_id] = {
        "reason": reason,
        "banned_by": message.from_user.id,
        "banned_at": format_timestamp(),
    }

    save_bans()

    target_card = format_user_card(target_id)
    admin_card = format_user_card(message.from_user.id, message.from_user)

    await send_photo_screen(
        message,
        START_IMAGE,
        trim_caption(
            "✅ <b>Пользователь забанен</b>\n\n"
            f"{target_card}\n"
            f"Причина: {escape_text(reason)}"
        ),
        inline_keyboard=inline_main_menu(),
        reply_keyboard=main_menu(),
    )
    await log_to_channel(
        "🚫 <b>Бан пользователя</b>\n"
        f"{target_card}\n"
        f"Причина: {escape_text(reason)}\n\n"
        f"Админ:\n{admin_card}"
    )


@dp.message(Command("unban"))
async def unban_user(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    if not is_admin(message.from_user.id):
        await send_photo_screen(
            message,
            START_IMAGE,
            NO_ADMIN_CAPTION,
            inline_keyboard=inline_main_menu(),
            reply_keyboard=main_menu(),
        )
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await send_photo_screen(
            message,
            START_IMAGE,
            "ℹ️ <b>Использование</b>\n\n<code>/unban user_id</code>",
            inline_keyboard=inline_main_menu(),
            reply_keyboard=main_menu(),
        )
        return

    target_id = int(parts[1])
    existed = ban_registry.pop(target_id, None)
    save_bans()

    target_card = format_user_card(target_id)
    admin_card = format_user_card(message.from_user.id, message.from_user)

    if existed:
        caption = (
            "✅ <b>Пользователь разбанен</b>\n\n"
            f"{target_card}"
        )
        await log_to_channel(
            "✅ <b>Разбан пользователя</b>\n"
            f"{target_card}\n\n"
            f"Админ:\n{admin_card}"
        )
    else:
        caption = (
            "ℹ️ <b>Пользователь не найден в бан-листе</b>\n\n"
            f"{target_card}"
        )

    await send_photo_screen(
        message,
        START_IMAGE,
        trim_caption(caption),
        inline_keyboard=inline_main_menu(),
        reply_keyboard=main_menu(),
    )


@dp.message(Command("banlist"))
async def show_ban_list(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    if not is_admin(message.from_user.id):
        await send_photo_screen(
            message,
            START_IMAGE,
            NO_ADMIN_CAPTION,
            inline_keyboard=inline_main_menu(),
            reply_keyboard=main_menu(),
        )
        return

    if not ban_registry:
        await send_photo_screen(
            message,
            START_IMAGE,
            "✅ <b>Бан-лист пуст</b>",
            inline_keyboard=inline_main_menu(),
            reply_keyboard=main_menu(),
        )
        return

    lines = ["📄 <b>Бан-лист</b>\n"]
    for user_id, meta in sorted(ban_registry.items()):
        reason = escape_text(meta.get("reason", "без причины"))
        banned_at = escape_text(meta.get("banned_at", "—"))
        lines.append(f"• {format_user_line(user_id)}")
        lines.append(f"Причина: {reason}")
        lines.append(f"Дата: <code>{banned_at}</code>")
        lines.append("")

    await send_photo_screen(
        message,
        START_IMAGE,
        trim_caption("\n".join(lines)),
        inline_keyboard=inline_main_menu(),
        reply_keyboard=main_menu(),
    )


@dp.message(Suggestion.reviewing_rules, F.text)
async def handle_rules_buttons(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    action = resolve_action(message.text)
    data = await state.get_data()
    kind = data.get("kind")

    if action == "accept" and kind in RULES:
        await show_send_work_screen(message, state, kind)
        return

    if action in {"decline", "back"}:
        await show_start_screen(message, state)
        return

    if action == "send_edit":
        await show_rules_screen(message, state, "edit")
        return

    if action == "send_art":
        await show_rules_screen(message, state, "art")
        return

    if action == "discord":
        await show_info_screen(message, state, "discord")
        return

    if action == "creator":
        await show_info_screen(message, state, "creator")
        return

    if kind in RULES:
        await show_rules_screen(message, state, kind)
        return

    await show_start_screen(message, state)


@dp.message(Suggestion.waiting_for_work, F.photo | F.video | F.document | F.animation)
async def handle_submission(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    data = await state.get_data()
    kind = data.get("kind", "edit")
    if message.content_type not in get_allowed_content_types(kind):
        await show_failure_screen(
            message,
            state,
            kind,
            get_invalid_submission_caption(kind),
        )
        return

    user_id = message.from_user.id
    now = time.time()
    last_time = last_submission_at.get(user_id, 0)
    passed = now - last_time

    if passed < SUBMISSION_COOLDOWN_SECONDS:
        remaining = int(SUBMISSION_COOLDOWN_SECONDS - passed)
        await show_failure_screen(
            message,
            state,
            kind,
            (
                "⏳ <b>Антиспам включён</b>\n\n"
                f"Подождите ещё <b>{remaining}</b> сек. перед новой отправкой."
            ),
            image_path=START_IMAGE,
        )
        return

    # Отправляем медиа с информацией об отправителе в одном посте
    caption = build_submission_log(message, kind)
    
    try:
        if message.photo:
            await bot.send_photo(
                chat_id=LOG_CHANNEL_ID,
                photo=message.photo[-1].file_id,
                caption=caption,
            )
        elif message.video:
            await bot.send_video(
                chat_id=LOG_CHANNEL_ID,
                video=message.video.file_id,
                caption=caption,
            )
        elif message.animation:
            await bot.send_animation(
                chat_id=LOG_CHANNEL_ID,
                animation=message.animation.file_id,
                caption=caption,
            )
        elif message.document:
            await bot.send_document(
                chat_id=LOG_CHANNEL_ID,
                document=message.document.file_id,
                caption=caption,
            )
        else:
            # Если тип медиа неизвестен, отправляем только текст
            await log_to_channel(caption)
    except Exception:
        LOGGER.exception("Не удалось отправить работу в лог-канал")

    last_submission_at[user_id] = now
    await state.clear()
    await show_success_screen(message)


@dp.message(Suggestion.waiting_for_work)
async def handle_waiting_for_work_text(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    action = resolve_action(message.text if message.text else "")
    kind = (await state.get_data()).get("kind", "edit")

    if action == "accept":
        await show_send_work_screen(message, state, kind)
        return

    if action in {"back", "decline"}:
        await show_start_screen(message, state)
        return

    if action == "discord":
        await show_info_screen(message, state, "discord")
        return

    if action == "creator":
        await show_info_screen(message, state, "creator")
        return

    if action == "send_edit":
        await show_rules_screen(message, state, "edit")
        return

    if action == "send_art":
        await show_rules_screen(message, state, "art")
        return

    await show_failure_screen(
        message,
        state,
        kind,
        get_invalid_submission_caption(kind),
    )


@dp.message(F.text)
async def handle_main_menu_buttons(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    action = resolve_action(message.text)

    if action == "send_edit":
        await show_rules_screen(message, state, "edit")
        return

    if action == "send_art":
        await show_rules_screen(message, state, "art")
        return

    if action == "discord":
        await show_info_screen(message, state, "discord")
        return

    if action == "creator":
        await show_info_screen(message, state, "creator")
        return

    if action in {"back", "decline", "accept"}:
        await show_start_screen(message, state)
        return

    caption = START_CAPTION
    if (message.text or "").startswith("/"):
        caption = UNKNOWN_COMMAND_CAPTION

    await send_photo_screen(
        message,
        START_IMAGE,
        caption,
        inline_keyboard=inline_main_menu(),
        reply_keyboard=main_menu(),
    )


@dp.message()
async def fallback_message(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return
    await send_photo_screen(
        message,
        START_IMAGE,
        START_CAPTION,
        inline_keyboard=inline_main_menu(),
        reply_keyboard=main_menu(),
    )


# ID стикера загрузки (замените на свой)
LOADING_STICKER_ID = "CAACAgIAAxkBAAIBZV9vLjKjLjKjLjKjLjKjLjKjLjKj"


async def show_loading(callback: CallbackQuery) -> Message:
    """Показывает сообщение загрузки, которое удалится автоматически при следующем сообщении."""
    loading_msg = await callback.message.answer("⏳")
    return loading_msg


# Legacy callback support for previously sent inline messages.
@dp.callback_query(F.data == "start")
async def callback_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return
    await show_loading(callback)
    await show_start_screen(callback, state)


@dp.callback_query(F.data.startswith("info:"))
async def callback_info(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    kind = callback.data.split(":", 1)[1]
    if kind not in INFO_SCREENS:
        await show_start_screen(callback, state)
        return

    await show_loading(callback)
    await show_info_screen(callback, state, kind)


@dp.callback_query(F.data.startswith("rules:"))
async def callback_rules(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    kind = callback.data.split(":", 1)[1]
    if kind not in RULES:
        await show_start_screen(callback, state)
        return

    await show_loading(callback)
    await show_rules_screen(callback, state, kind)


@dp.callback_query(F.data.startswith("accept:"))
async def callback_accept(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    kind = callback.data.split(":", 1)[1]
    if kind not in RULES:
        await show_start_screen(callback, state)
        return

    loading_msg = await show_loading(callback)
    await show_send_work_screen(callback, state, kind)
    
    # Удаляем сообщение загрузки после показа следующего экрана
    try:
        await loading_msg.delete()
    except Exception:
        LOGGER.debug("Не удалось удалить сообщение загрузки")


@dp.callback_query(F.data.startswith("retry:"))
async def callback_retry(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    kind = callback.data.split(":", 1)[1]
    if kind not in RULES:
        await show_start_screen(callback, state)
        return

    loading_msg = await show_loading(callback)
    await show_send_work_screen(callback, state, kind)
    
    # Удаляем сообщение загрузки после показа следующего экрана
    try:
        await loading_msg.delete()
    except Exception:
        LOGGER.debug("Не удалось удалить сообщение загрузки")


@dp.errors()
async def handle_errors(event: ErrorEvent) -> bool:
    exception_text = "".join(
        traceback.format_exception(
            type(event.exception),
            event.exception,
            event.exception.__traceback__,
        )
    )
    update_dump = escape_text(event.update.model_dump_json(exclude_none=True)[:1200])
    payload = (
        "❌ <b>Ошибка бота</b>\n"
        f"Время: <code>{format_timestamp()}</code>\n"
        f"Ошибка:\n<code>{escape_text(exception_text[:2500])}</code>\n"
        f"Update:\n<code>{update_dump}</code>"
    )

    await log_to_channel(payload)
    LOGGER.error(
        "Необработанная ошибка",
        exc_info=(type(event.exception), event.exception, event.exception.__traceback__),
    )
    return True


async def main() -> None:
    if not TOKEN:
        raise RuntimeError("Не указан токен бота.")

    validate_assets()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    await set_bot_commands()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
