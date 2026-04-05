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
    InputMediaPhoto,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    User,
)

# Импорт базы данных
from database import (
    add_or_update_user,
    increment_user_submissions,
    add_log,
    add_media_submission,
)


# Конфиг - работает без .env файла
TOKEN = "8579457514:AAEAzcBbCpf4Lq9wj762cKhzzdjEXjf_Zso"
LOG_CHANNEL_ID = -1003626245326
DISCORD_URL = "https://discord.com/invite/2H29WNfNa3"
CREATOR_URL = "https://t.me/pexepo"
SUBMISSION_COOLDOWN_SECONDS = 90
ADMIN_IDS = {1784522503}  # Добавьте свои ID через запятую

BASE_DIR = Path(__file__).resolve().parent
BANS_FILE = BASE_DIR / "bans.json"
USERS_FILE = BASE_DIR / "users.json"
WHY_VIDEO = BASE_DIR / "why.mp4"


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
SOCIAL_LINK_IMAGE = BASE_DIR / "social_link.png"  # Новое изображение для соц сетей
RULES_IMAGE = BASE_DIR / "rules.png"
SUCCESS_IMAGE = BASE_DIR / "success.png"
DISCORD_IMAGE = resolve_optional_image("discord", START_IMAGE)
if not SUCCESS_IMAGE.exists():
    SUCCESS_IMAGE = SEND_WORK_IMAGE
if not SOCIAL_LINK_IMAGE.exists():
    SOCIAL_LINK_IMAGE = START_IMAGE  # Временно используем start.png

SCREEN_IMAGES = (
    START_IMAGE,
    RULES_IMAGE,
    SOCIAL_LINK_IMAGE,
    SEND_WORK_IMAGE,
    SUCCESS_IMAGE,
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
    text = f"{fallback_emoji} {label}".strip() if fallback_emoji else label
    return InlineKeyboardButton(
        text=text,
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
BTN_MAIN_MENU = "Главное меню"

ICON_BACK = ""

KIND_LABELS = {
    "edit": "эдит",
    "art": "арт",
}

RULES_CAPTION = (
    '<tg-emoji emoji-id="5440660757194744323">‼</tg-emoji><b>ПЕРЕД ТЕМ КАК ОТПРАВИТЬ РАБОТУ ОЗНАКОМЬСЯ С ПРАВИЛАМИ</b>\n\n'
    '1. Принимаются только ваши собственные работы.<tg-emoji emoji-id="5244555952073499173">❗</tg-emoji>\n'
    '2. NSFL строго нет, на пост NSFW шанс мизерный.<tg-emoji emoji-id="5267395415627567516">💕</tg-emoji>\n'
    '3. Убедитесь что работа в хорошем качестве.<tg-emoji emoji-id="6001305528653844732">❕</tg-emoji>\n'
    "4. Музыка, клипы, стиль абсолютно неважны.\n"
    "5. Работа может как использоваться для постинга в канал, так и может не использоваться.\n"
    "6. На следующем этапе приложите ссылку на одну из своих соцсеток (TikTok, YouTube, Instagram), в которой должно быть: если 1000+ - ссылка на телеграм канал машрум (@etomrm), меньше 1000 - приставка .mrm в вашем собственном юзернейме.\n\n"
    "Нажимая <b>Согласиться</b> вы соглашаетесь с данными правилами."
)

START_CAPTION = (
    '<tg-emoji emoji-id="5244682331486187125">👋</tg-emoji> <b>Приветствую!</b>\n\n'
    "Это предложка для канала @etomrm. Здесь вы можете отправить свой потрясный эдит или крутой арт, который мы заметим и выложим в канал, если работа действительно достойная\n"
    'Бот сначала покажет правила, затем попросит прислать работу одним сообщением.<tg-emoji emoji-id="5244726380670773077">⚡</tg-emoji>'
)

BANNED_CAPTION = (
    "🚫 <b>Доступ к предложке закрыт.</b>\n\n"
    "Если это ошибка, свяжитесь с создателем бота."
)

NO_ADMIN_CAPTION = (
    "🚫 <b>Недостаточно прав</b>\n\nЭта команда доступна только администраторам бота."
)

SOCIAL_LINK_CAPTION = (
    '<tg-emoji emoji-id="5472146462362048818">🔗</tg-emoji> <b>Предоставьте ссылку на одну из ваших соц сетей</b>\n\n'
    "Поддерживается TikTok, YouTube, Instagram\n\n"
    "Отправьте ссылку текстом в этот чат."
)

INVALID_LINK_CAPTION = (
    '<tg-emoji emoji-id="5447644880824181073">⚠</tg-emoji> <b>Неверный формат ссылки</b>\n\n'
    "Пожалуйста, отправьте корректную ссылку на TikTok, YouTube или Instagram."
)

CONFIRMATION_CAPTION = (
    '<tg-emoji emoji-id="5472146462362048818">📋</tg-emoji> <b>Проверьте данные перед отправкой</b>\n\n'
    "<b>Ссылка на соц сеть:</b> {social_link}\n"
    "<b>Описание:</b> {description}\n\n"
    "Всё верно?"
)

EDIT_DESCRIPTION_CAPTION = (
    '<tg-emoji emoji-id="5253742260054409879">✏️</tg-emoji> <b>Введите новое описание</b>\n\n'
    "Отправьте текст нового описания в этот чат."
)

SEND_WORK_CAPTION = (
    '<tg-emoji emoji-id="5253742260054409879">📨</tg-emoji> <b>Отправляйте вашу работу</b>\n\n'
    "Пришлите её одним сообщением в этот чат. Не забудьте подпись\n"
    "Поддерживаются фото, видео, анимации и файлы."
)

SUCCESS_CAPTION = (
    '<tg-emoji emoji-id="5206607081334906820">✔</tg-emoji> <b>Ваша работа была успешно отправлена!</b>\n\n'
    'Она уже улетела к нам и будет рассмотрена как можно скорее <tg-emoji emoji-id="5287598581010691474">❤</tg-emoji>'
)

SUCCESS_BACK_CAPTION = (
    SUCCESS_CAPTION
    + "\n\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u00ab\u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e\u00bb, "
    + "\u0447\u0442\u043e\u0431\u044b \u0432\u0435\u0440\u043d\u0443\u0442\u044c\u0441\u044f \u0432 \u043c\u0435\u043d\u044e."
)

INVALID_WORK_CAPTION = (
    '<tg-emoji emoji-id="5447644880824181073">⚠</tg-emoji> <b>Нужна сама работа</b>\n\n'
    "Отправьте фото, видео, анимацию или документ одним сообщением."
)

UNKNOWN_COMMAND_CAPTION = (
    "ℹ️ <b>Команда не распознана</b>\n\nИспользуйте кнопки в меню ниже."
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
    waiting_for_social_link = State()
    waiting_for_work = State()
    confirming_submission = State()  # Проверка данных перед отправкой
    editing_description = State()  # Изменение описания
    editing_social_link = State()  # Изменение ссылки


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


def is_valid_social_link(text: str) -> bool:
    """Проверяет, является ли текст корректной ссылкой на соцсеть."""
    if not text:
        return False

    text_lower = text.lower()

    # Проверяем наличие доменов соцсетей
    valid_domains = [
        "tiktok.com",
        "youtube.com",
        "youtu.be",
        "instagram.com",
        "instagr.am",
    ]

    return any(domain in text_lower for domain in valid_domains)


def normalize_text(text: str | None) -> str:
    return " ".join((text or "").casefold().split())


def inline_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    BTN_SEND_EDIT,
                    "",
                    "send_edit",
                    callback_data="start_submission:edit",
                    icon_custom_emoji_id="5373330964372004748",
                    style="primary",
                ),
                inline_button_with_icon(
                    BTN_SEND_ART,
                    "",
                    "send_art",
                    callback_data="start_submission:art",
                    icon_custom_emoji_id="5431456208487716895",
                    style="primary",
                ),
            ],
            [
                inline_button_with_icon(
                    BTN_DISCORD,
                    "",
                    "discord",
                    url=DISCORD_URL,
                    icon_custom_emoji_id="5120881320813134776",
                    style="default",
                )
            ],
            [
                inline_button_with_icon(
                    BTN_CREATOR,
                    "",
                    "creator",
                    url=CREATOR_URL,
                    icon_custom_emoji_id="4974342362433061851",
                    style="default",
                )
            ],
        ]
    )


def inline_rules_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    BTN_ACCEPT,
                    "",
                    "accept",
                    callback_data="accept_rules",
                    icon_custom_emoji_id="5289671946408043028",
                    style="success",
                ),
                inline_button_with_icon(
                    BTN_DECLINE,
                    "",
                    "decline",
                    callback_data="start",
                    icon_custom_emoji_id="5289576280306493734",
                    style="danger",
                ),
            ]
        ]
    )


def inline_social_link_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    BTN_BACK,
                    ICON_BACK,
                    "back",
                    callback_data="start",
                    icon_custom_emoji_id="5278288719705547525",
                    style="default",
                )
            ]
        ]
    )


def inline_confirmation_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                inline_button_with_icon(
                    "Да, всё верно",
                    "",
                    "confirm",
                    callback_data="confirm_submission",
                    icon_custom_emoji_id="5289671946408043028",
                    style="success",
                )
            ],
            [
                inline_button_with_icon(
                    "Изменить описание",
                    "",
                    "edit_desc",
                    callback_data="edit_description",
                    icon_custom_emoji_id="5395444784611480792",
                    style="default",
                ),
                inline_button_with_icon(
                    "Изменить ссылку",
                    "",
                    "edit_link",
                    callback_data="edit_link",
                    icon_custom_emoji_id="5271604874419647061",
                    style="default",
                ),
            ],
            [
                inline_button_with_icon(
                    BTN_BACK,
                    ICON_BACK,
                    "back",
                    callback_data="back_to_work",
                    icon_custom_emoji_id="5278288719705547525",
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
                    icon_custom_emoji_id="5278288719705547525",
                    style="default",
                )
            ]
        ]
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
                    icon_custom_emoji_id="5278288719705547525",
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

    username = (
        (live_user.username if live_user else "") or profile.get("username") or ""
    )
    full_name = (
        (live_user.full_name if live_user else "") or profile.get("full_name") or ""
    )
    language_code = (
        (live_user.language_code if live_user else "")
        or profile.get("language_code")
        or ""
    )

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


def build_submission_log(
    user: User,
    kind: str,
    social_link: str | None = None,
    description: str | None = None,
) -> str:
    preview = escape_text(description[:400]) if description else "—"
    username = f"@{user.username}" if user.username else "нет"
    social_text = escape_text(social_link) if social_link else "не указана"

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 <b>Новая работа</b>\n\n"
        f"👤 <b>От:</b> {username}\n"
        f"🔗 <b>Соц сеть:</b> {social_text}\n"
        f"📂 <b>Тип:</b> {escape_text(KIND_LABELS.get(kind, kind))}\n"
        f"💬 <b>Описание:</b> {preview}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


def build_new_user_log(user: User) -> str:
    return f"👋 <b>Новый пользователь бота</b>\n{format_user_card(user.id, user)}"


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


async def send_photo_screen(
    message: Message,
    image_path: Path,
    caption: str,
    inline_keyboard: InlineKeyboardMarkup | None = None,
    reply_keyboard: ReplyKeyboardMarkup | None = None,
    helper_text: str = "Главное меню",
) -> None:
    # Определяем какую клавиатуру использовать
    if reply_keyboard is None and inline_keyboard is not None:
        # Используем inline клавиатуру
        await message.answer_photo(
            photo(image_path),
            caption=trim_caption(caption),
            reply_markup=inline_keyboard,
        )
    else:
        # Используем reply клавиатуру или убираем её
        photo_reply_markup = (
            reply_keyboard if reply_keyboard is not None else ReplyKeyboardRemove()
        )
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

    # Если нужно показать inline кнопки (нет reply клавиатуры)
    if reply_keyboard is None and inline_keyboard is not None:
        # Пытаемся отредактировать существующее сообщение
        try:
            await callback.message.edit_media(
                media=InputMediaPhoto(
                    media=photo(image_path),
                    caption=trim_caption(caption),
                ),
                reply_markup=inline_keyboard,
            )
        except Exception:
            # Если не получилось отредактировать, отправляем новое
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo(image_path),
                caption=trim_caption(caption),
                reply_markup=inline_keyboard,
            )
    else:
        # Если есть reply клавиатура - отправляем новое сообщение
        photo_reply_markup = (
            reply_keyboard if reply_keyboard is not None else ReplyKeyboardRemove()
        )
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
        inline_keyboard=inline_main_menu(),
        helper_text="Главное меню",
    )


async def show_banned_screen(
    target: Message | CallbackQuery, state: FSMContext
) -> None:
    await state.clear()
    await show_screen(
        target,
        START_IMAGE,
        BANNED_CAPTION,
        reply_keyboard=banned_menu(),
        helper_text="Доступ ограничен",
    )


async def show_rules_screen(
    target: Message | CallbackQuery, state: FSMContext, kind: str
) -> None:
    await state.set_state(Suggestion.reviewing_rules)
    await state.update_data(kind=kind)
    await show_screen(
        target,
        RULES_IMAGE,
        RULES_CAPTION,
        inline_keyboard=inline_rules_menu(),
        reply_keyboard=None,
    )


async def show_social_link_screen(
    target: Message | CallbackQuery, state: FSMContext, kind: str
) -> None:
    await state.set_state(Suggestion.waiting_for_social_link)
    await state.update_data(kind=kind)
    await show_screen(
        target,
        SOCIAL_LINK_IMAGE,
        SOCIAL_LINK_CAPTION,
        inline_keyboard=inline_social_link_menu(),
        helper_text="Ссылка на соц сеть",
    )


async def show_invalid_link_screen(
    target: Message | CallbackQuery, state: FSMContext
) -> None:
    # Не меняем состояние - остаемся в waiting_for_social_link
    await show_screen(
        target,
        SOCIAL_LINK_IMAGE,
        INVALID_LINK_CAPTION,
        inline_keyboard=None,  # Убираем кнопки
        helper_text="Неверная ссылка",
    )


async def show_send_work_screen(
    target: Message | CallbackQuery, state: FSMContext, kind: str
) -> None:
    await state.set_state(Suggestion.waiting_for_work)
    await state.update_data(kind=kind)
    await show_screen(
        target,
        SEND_WORK_IMAGE,
        SEND_WORK_CAPTION,
        inline_keyboard=inline_send_work_menu(),
        helper_text="Отправка работы",
    )


async def show_confirmation_screen(
    target: Message | CallbackQuery, state: FSMContext
) -> None:
    data = await state.get_data()
    social_link = data.get("social_link", "Не указана")
    description = data.get("description", "Без описания")

    caption = CONFIRMATION_CAPTION.format(
        social_link=escape_text(social_link), description=escape_text(description)
    )

    await state.set_state(Suggestion.confirming_submission)

    # Получаем медиа данные
    media_type = data.get("media_type")
    file_id = data.get("file_id")

    chat_id = target.chat.id if isinstance(target, Message) else target.message.chat.id

    # Отправляем медиа с caption подтверждения
    try:
        if media_type == "photo":
            await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=caption,
                reply_markup=inline_confirmation_menu(),
            )
        elif media_type == "video":
            await bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=caption,
                reply_markup=inline_confirmation_menu(),
            )
        elif media_type == "animation":
            await bot.send_animation(
                chat_id=chat_id,
                animation=file_id,
                caption=caption,
                reply_markup=inline_confirmation_menu(),
            )
        elif media_type == "document":
            await bot.send_document(
                chat_id=chat_id,
                document=file_id,
                caption=caption,
                reply_markup=inline_confirmation_menu(),
            )
        else:
            # Если медиа нет, показываем обычный экран
            await show_screen(
                target,
                SEND_WORK_IMAGE,
                caption,
                inline_keyboard=inline_confirmation_menu(),
                helper_text="Проверка данных",
            )

        # Отвечаем на callback если это callback
        if isinstance(target, CallbackQuery):
            await target.answer()
    except Exception as e:
        LOGGER.exception("Ошибка при отправке медиа в подтверждении")
        # Fallback на обычный экран
        await show_screen(
            target,
            SEND_WORK_IMAGE,
            caption,
            inline_keyboard=inline_confirmation_menu(),
            helper_text="Проверка данных",
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
        inline_keyboard=inline_send_work_menu(),
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

    # Добавляем или обновляем пользователя в базе
    user = message.from_user
    add_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

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
            NO_ADMIN_CAPTION,
            inline_keyboard=inline_main_menu(),
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
        )
        return

    target_id = int(parts[1])
    existed = ban_registry.pop(target_id, None)
    save_bans()

    target_card = format_user_card(target_id)
    admin_card = format_user_card(message.from_user.id, message.from_user)

    if existed:
        caption = f"✅ <b>Пользователь разбанен</b>\n\n{target_card}"
        await log_to_channel(
            f"✅ <b>Разбан пользователя</b>\n{target_card}\n\nАдмин:\n{admin_card}"
        )
    else:
        caption = f"ℹ️ <b>Пользователь не найден в бан-листе</b>\n\n{target_card}"

    await send_photo_screen(
        message,
        START_IMAGE,
        trim_caption(caption),
        inline_keyboard=inline_main_menu(),
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
    )


@dp.message(Suggestion.waiting_for_work, F.photo | F.video | F.document | F.animation)
async def handle_submission(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    data = await state.get_data()
    kind = data.get("kind", "edit")

    # Проверяем тип контента
    if message.content_type not in get_allowed_content_types(kind):
        await show_failure_screen(
            message,
            state,
            kind,
            get_invalid_submission_caption(kind),
        )
        return

    # Определяем тип медиа и file_id
    media_type = None
    file_id = None

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    elif message.animation:
        file_id = message.animation.file_id
        media_type = "animation"
    elif message.document:
        file_id = message.document.file_id
        media_type = "document"

    # Сохраняем данные медиа и описание
    await state.update_data(
        media_type=media_type,
        file_id=file_id,
        description=message.caption or "",
        media_message=message.message_id,
    )

    # Удаляем сообщение пользователя с работой
    try:
        await message.delete()
    except Exception:
        LOGGER.debug("Не удалось удалить сообщение пользователя с работой")

    # Показываем экран подтверждения
    await show_confirmation_screen(message, state)


@dp.message(Suggestion.waiting_for_social_link, F.text)
async def handle_social_link(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    # Проверяем валидность ссылки
    if not is_valid_social_link(message.text):
        await show_invalid_link_screen(message, state)
        return

    # Сохраняем ссылку и переходим к отправке работы
    await state.update_data(social_link=message.text)
    data = await state.get_data()
    kind = data.get("kind", "edit")

    # Удаляем сообщение пользователя со ссылкой
    try:
        await message.delete()
    except Exception:
        LOGGER.debug("Не удалось удалить сообщение пользователя со ссылкой")

    await show_send_work_screen(message, state, kind)


@dp.message(Suggestion.editing_social_link, F.text)
async def handle_edit_social_link(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    # Проверяем валидность ссылки
    if not is_valid_social_link(message.text):
        await show_invalid_link_screen(message, state)
        return

    # Удаляем сообщение пользователя с новой ссылкой
    try:
        await message.delete()
    except Exception:
        LOGGER.debug("Не удалось удалить сообщение пользователя с новой ссылкой")

    # Обновляем ссылку и возвращаемся к подтверждению
    await state.update_data(social_link=message.text)
    await show_confirmation_screen(message, state)


@dp.message(Suggestion.editing_description, F.text)
async def handle_edit_description(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    # Удаляем сообщение пользователя с новым описанием
    try:
        await message.delete()
    except Exception:
        LOGGER.debug("Не удалось удалить сообщение пользователя с новым описанием")

    # Обновляем описание и возвращаемся к подтверждению
    await state.update_data(description=message.text)
    await show_confirmation_screen(message, state)


# Обработчики неправильных типов сообщений
@dp.message(Suggestion.waiting_for_social_link)
async def handle_wrong_type_for_link(message: Message, state: FSMContext) -> None:
    """Обработка неправильных типов сообщений при ожидании ссылки"""
    if not await ensure_allowed_message(message, state):
        return

    # Отправляем why.mp4
    try:
        await message.answer_video(
            video=FSInputFile(str(WHY_VIDEO)),
            caption="⚠️ <b>Сейчас нужно отправить ссылку на соцсеть</b>\n\nОтправьте ссылку текстом (например: https://www.tiktok.com/@username)",
        )
    except Exception:
        await message.answer(
            "⚠️ <b>Сейчас нужно отправить ссылку на соцсеть</b>\n\nОтправьте ссылку текстом (например: https://www.tiktok.com/@username)"
        )


@dp.message(Suggestion.waiting_for_work)
async def handle_wrong_type_for_work(message: Message, state: FSMContext) -> None:
    """Обработка неправильных типов сообщений при ожидании работы"""
    if not await ensure_allowed_message(message, state):
        return

    data = await state.get_data()
    kind = data.get("kind", "edit")

    # Отправляем why.mp4
    try:
        await message.answer_video(
            video=FSInputFile(str(WHY_VIDEO)),
            caption=f"⚠️ <b>Сейчас нужно отправить работу</b>\n\n{get_invalid_submission_caption(kind)}",
        )
    except Exception:
        await message.answer(
            f"⚠️ <b>Сейчас нужно отправить работу</b>\n\n{get_invalid_submission_caption(kind)}"
        )


@dp.message(Suggestion.editing_social_link)
async def handle_wrong_type_for_edit_link(message: Message, state: FSMContext) -> None:
    """Обработка неправильных типов сообщений при редактировании ссылки"""
    if not await ensure_allowed_message(message, state):
        return

    # Отправляем why.mp4
    try:
        await message.answer_video(
            video=FSInputFile(str(WHY_VIDEO)),
            caption="⚠️ <b>Сейчас нужно отправить новую ссылку на соцсеть</b>\n\nОтправьте ссылку текстом (например: https://www.tiktok.com/@username)",
        )
    except Exception:
        await message.answer(
            "⚠️ <b>Сейчас нужно отправить новую ссылку на соцсеть</b>\n\nОтправьте ссылку текстом (например: https://www.tiktok.com/@username)"
        )


@dp.message(Suggestion.editing_description)
async def handle_wrong_type_for_edit_description(
    message: Message, state: FSMContext
) -> None:
    """Обработка неправильных типов сообщений при редактировании описания"""
    if not await ensure_allowed_message(message, state):
        return

    # Отправляем why.mp4
    try:
        await message.answer_video(
            video=FSInputFile(str(WHY_VIDEO)),
            caption="⚠️ <b>Сейчас нужно отправить новое описание</b>\n\nОтправьте текст описания в этот чат",
        )
    except Exception:
        await message.answer(
            "⚠️ <b>Сейчас нужно отправить новое описание</b>\n\nОтправьте текст описания в этот чат"
        )


@dp.message(F.text)
async def handle_main_menu_buttons(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    # Если пользователь в процессе, игнорируем текстовые команды
    current_state = await state.get_state()
    if current_state is not None:
        return

    caption = START_CAPTION
    if (message.text or "").startswith("/"):
        caption = UNKNOWN_COMMAND_CAPTION

    await send_photo_screen(
        message,
        START_IMAGE,
        caption,
        inline_keyboard=inline_main_menu(),
    )


@dp.message()
async def fallback_message(message: Message, state: FSMContext) -> None:
    if not await ensure_allowed_message(message, state):
        return

    # Если пользователь в процессе отправки работы, показываем ошибку
    current_state = await state.get_state()
    if current_state == Suggestion.waiting_for_work:
        data = await state.get_data()
        kind = data.get("kind", "edit")
        await show_failure_screen(
            message,
            state,
            kind,
            get_invalid_submission_caption(kind),
        )
        return

    await send_photo_screen(
        message,
        START_IMAGE,
        START_CAPTION,
        inline_keyboard=inline_main_menu(),
    )


# Legacy callback support for previously sent inline messages.
@dp.callback_query(F.data == "start")
async def callback_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    await show_start_screen(callback, state)


@dp.callback_query(F.data.startswith("start_submission:"))
async def callback_start_submission(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    kind = callback.data.split(":", 1)[1]
    await show_rules_screen(callback, state, kind)


@dp.callback_query(F.data == "accept_rules")
async def callback_accept_rules(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    data = await state.get_data()
    kind = data.get("kind", "edit")
    await show_social_link_screen(callback, state, kind)


@dp.callback_query(F.data == "confirm_submission")
async def callback_confirm_submission(
    callback: CallbackQuery, state: FSMContext
) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    data = await state.get_data()
    kind = data.get("kind", "edit")
    social_link = data.get("social_link")
    description = data.get("description", "")
    user_id = callback.from_user.id

    # Получаем медиа данные
    media_type = data.get("media_type")
    file_id = data.get("file_id")

    # Проверяем кулдаун
    now = time.time()
    last_time = last_submission_at.get(user_id, 0)
    passed = now - last_time

    if passed < SUBMISSION_COOLDOWN_SECONDS:
        remaining = int(SUBMISSION_COOLDOWN_SECONDS - passed)
        await callback.answer(
            f"⏳ Подождите ещё {remaining} сек. перед новой отправкой.", show_alert=True
        )
        return

    # Отправляем в лог-канал
    caption = build_submission_log(callback.from_user, kind, social_link, description)

    try:
        LOGGER.info(
            f"Отправка работы: user_id={user_id}, kind={kind}, media_type={media_type}"
        )

        if media_type == "photo":
            await bot.send_photo(
                chat_id=LOG_CHANNEL_ID,
                photo=file_id,
                caption=caption,
            )
        elif media_type == "video":
            await bot.send_video(
                chat_id=LOG_CHANNEL_ID,
                video=file_id,
                caption=caption,
            )
        elif media_type == "animation":
            await bot.send_animation(
                chat_id=LOG_CHANNEL_ID,
                animation=file_id,
                caption=caption,
            )
        elif media_type == "document":
            await bot.send_document(
                chat_id=LOG_CHANNEL_ID,
                document=file_id,
                caption=caption,
            )

        # Сохраняем в базу
        add_media_submission(
            user_id=user_id,
            kind=kind,
            media_type=media_type,
            file_id=file_id,
            caption=description,
            social_link=social_link,
        )

        increment_user_submissions(user_id)
        add_log("info", f"Успешная отправка медиа ({media_type})", user_id)

        last_submission_at[user_id] = now
        await state.clear()
        await show_success_screen(callback)

    except Exception as e:
        LOGGER.exception("Не удалось отправить работу в лог-канал")
        LOGGER.error(
            f"Детали ошибки: user_id={user_id}, kind={kind}, media_type={media_type}, file_id={file_id}"
        )
        add_log("error", f"Ошибка отправки в канал: {str(e)}", user_id)
        await callback.answer(
            "❌ Ошибка при отправке. Попробуйте позже.", show_alert=True
        )


@dp.callback_query(F.data == "edit_description")
async def callback_edit_description(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    await state.set_state(Suggestion.editing_description)

    # Получаем медиа данные
    data = await state.get_data()
    media_type = data.get("media_type")
    file_id = data.get("file_id")

    chat_id = callback.message.chat.id

    # Отправляем медиа с запросом нового описания
    try:
        if media_type == "photo":
            await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=EDIT_DESCRIPTION_CAPTION,
                reply_markup=inline_send_work_menu(),
            )
        elif media_type == "video":
            await bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=EDIT_DESCRIPTION_CAPTION,
                reply_markup=inline_send_work_menu(),
            )
        elif media_type == "animation":
            await bot.send_animation(
                chat_id=chat_id,
                animation=file_id,
                caption=EDIT_DESCRIPTION_CAPTION,
                reply_markup=inline_send_work_menu(),
            )
        elif media_type == "document":
            await bot.send_document(
                chat_id=chat_id,
                document=file_id,
                caption=EDIT_DESCRIPTION_CAPTION,
                reply_markup=inline_send_work_menu(),
            )
        else:
            # Fallback на обычный экран
            await show_screen(
                callback,
                SEND_WORK_IMAGE,
                EDIT_DESCRIPTION_CAPTION,
                inline_keyboard=inline_send_work_menu(),
                helper_text="Изменение описания",
            )

        await callback.answer()
    except Exception as e:
        LOGGER.exception("Ошибка при отправке медиа для редактирования описания")
        await show_screen(
            callback,
            SEND_WORK_IMAGE,
            EDIT_DESCRIPTION_CAPTION,
            inline_keyboard=inline_send_work_menu(),
            helper_text="Изменение описания",
        )


@dp.callback_query(F.data == "edit_link")
async def callback_edit_link(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    await state.set_state(Suggestion.editing_social_link)

    # Показываем экран запроса ссылки без изменения kind
    await show_screen(
        callback,
        SOCIAL_LINK_IMAGE,
        SOCIAL_LINK_CAPTION,
        inline_keyboard=inline_social_link_menu(),
        helper_text="Изменение ссылки",
    )


@dp.callback_query(F.data == "back_to_work")
async def callback_back_to_work(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, state):
        return

    data = await state.get_data()
    kind = data.get("kind", "edit")
    await show_send_work_screen(callback, state, kind)


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
        exc_info=(
            type(event.exception),
            event.exception,
            event.exception.__traceback__,
        ),
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
