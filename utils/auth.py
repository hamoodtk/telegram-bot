from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import USER_IDS


def is_allowed_user(user_id: int | None) -> bool:
    return bool(user_id) and (not USER_IDS or user_id in USER_IDS)


def is_private_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type == "private")


async def ensure_authorized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user or not is_private_chat(update):
        if update.message:
            await update.message.reply_text("هذا البوت يعمل فقط في المحادثة الخاصة.")
        elif update.callback_query:
            await update.callback_query.answer("هذا البوت خاص فقط.", show_alert=True)
        return False

    if not is_allowed_user(user.id):
        message = (
            "⛔ هذا البوت مغلق ومتاح فقط للمستخدمين المصرح لهم.\n\n"
            "إذا كنت تعتقد أن هذا خطأ، تواصل مع صاحب البوت."
        )
        if update.message:
            await update.message.reply_text(message)
        elif update.callback_query:
            await update.callback_query.answer("غير مصرح لك.", show_alert=True)
        return False

    return True


def display_name(user) -> str:
    pieces = [piece for piece in [user.first_name, user.last_name] if piece]
    if pieces:
        return " ".join(pieces)
    if user.username:
        return f"@{user.username}"
    return str(user.id)

