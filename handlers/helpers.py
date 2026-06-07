from __future__ import annotations

from telegram import InlineKeyboardMarkup, Update


async def respond(update: Update, text: str, reply_markup=None) -> None:
    if update.callback_query:
        query = update.callback_query
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup)
        except Exception:
            await query.message.reply_text(text, reply_markup=reply_markup)
        return

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def answer_callback(update: Update, text: str | None = None, alert: bool = False) -> None:
    if update.callback_query:
        await update.callback_query.answer(text or "", show_alert=alert)


async def send_home(update: Update, text: str, keyboard) -> None:
    await respond(update, text, reply_markup=keyboard)

