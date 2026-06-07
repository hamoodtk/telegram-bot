from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import Database
from bot.handlers.helpers import answer_callback, respond
from bot.keyboards.common import (
    back_to_home_keyboard,
    main_menu_keyboard,
    main_reply_keyboard,
    reports_menu_keyboard,
)
from bot.utils.auth import display_name, ensure_authorized
from bot.utils.constants import HOME_LABEL, MAIN_MENU_LABELS, REFRESH_LABEL, CANCEL_LABEL
from bot.utils.state import clear_pending, get_pending

from bot.handlers import goals, health, notes, reports, settings, tasks, worship


def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.application.bot_data["db"]


async def _show_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db = _db(context)
    db.register_user(user)
    profile = db.get_user_profile(user.id)
    streak = profile["effective_streak"] if profile else 0
    points = profile["total_points"] if profile else 0
    text = (
        f"مرحبًا {display_name(user)} 👋\n\n"
        f"هذا بوتك الشخصي المغلق للمداومة اليومية.\n"
        f"النقاط الحالية: {points}\n"
        f"السلسلة الحالية: {streak}\n\n"
        f"اختر من القائمة بالأسفل أو من الأزرار التالية:"
    )
    clear_pending(context)
    if update.message:
        await update.message.reply_text(text, reply_markup=main_reply_keyboard())
    else:
        await respond(update, text, reply_markup=main_menu_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized(update, context):
        return
    await _show_main(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized(update, context):
        return
    text = (
        "ℹ️ مساعدة سريعة\n\n"
        "• استخدم /start لفتح الواجهة الرئيسية.\n"
        "• الأزرار في الأسفل للوصول السريع للأقسام.\n"
        "• عند طلب إدخال نص، أرسل البيانات بالشكل المطلوب في الرسالة.\n"
        "• /cancel لإلغاء أي عملية قيد التنفيذ."
    )
    await respond(update, text, reply_markup=main_reply_keyboard())


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized(update, context):
        return
    clear_pending(context)
    await respond(update, "تم إلغاء العملية الحالية.", reply_markup=main_reply_keyboard())


async def handle_main_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    text = (update.message.text or "").strip()
    if text == MAIN_MENU_LABELS["worship"]:
        await worship.show_menu(update, context)
        return True
    if text == MAIN_MENU_LABELS["health"]:
        await health.show_menu(update, context)
        return True
    if text == MAIN_MENU_LABELS["notes"]:
        await notes.show_menu(update, context)
        return True
    if text == MAIN_MENU_LABELS["tasks"]:
        await tasks.show_menu(update, context)
        return True
    if text == MAIN_MENU_LABELS["goals"]:
        await goals.show_menu(update, context)
        return True
    if text == MAIN_MENU_LABELS["leaderboard"]:
        await reports.show_leaderboard_menu(update, context)
        return True
    if text == MAIN_MENU_LABELS["reports"]:
        await reports.show_reports_menu(update, context)
        return True
    if text == MAIN_MENU_LABELS["settings"]:
        await settings.show_menu(update, context)
        return True
    if text in {HOME_LABEL, REFRESH_LABEL}:
        await _show_main(update, context)
        return True
    if text == CANCEL_LABEL:
        await cancel(update, context)
        return True
    return False


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized(update, context):
        return

    db = _db(context)
    db.register_user(update.effective_user)
    text = (update.message.text or "").strip()

    if text in {HOME_LABEL, REFRESH_LABEL}:
        await _show_main(update, context)
        return
    if text == CANCEL_LABEL:
        clear_pending(context)
        await respond(update, "تم إلغاء العملية الحالية.", reply_markup=main_reply_keyboard())
        return

    pending_action, pending_data = get_pending(context)
    if pending_action:
        handled = await dispatch_pending(update, context, pending_action, pending_data)
        if handled:
            return

    if await handle_main_menu_text(update, context):
        return

    await respond(
        update,
        "استخدم الأزرار الموجودة أو /help لمعرفة طريقة الاستخدام.",
        reply_markup=main_reply_keyboard(),
    )


async def dispatch_pending(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, data: dict) -> bool:
    if action.startswith("worship:"):
        return await worship.process_pending(update, context, action, data)
    if action.startswith("health:"):
        return await health.process_pending(update, context, action, data)
    if action.startswith("notes:"):
        return await notes.process_pending(update, context, action, data)
    if action.startswith("tasks:"):
        return await tasks.process_pending(update, context, action, data)
    if action.startswith("goals:"):
        return await goals.process_pending(update, context, action, data)
    return False


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized(update, context):
        return

    db = _db(context)
    db.register_user(update.effective_user)
    query = update.callback_query
    await answer_callback(update)
    data = query.data or ""

    if data == "menu:home":
        clear_pending(context)
        await _show_main(update, context)
        return
    if data == "menu:worship":
        await worship.show_menu(update, context)
        return
    if data == "menu:health":
        await health.show_menu(update, context)
        return
    if data == "menu:notes":
        await notes.show_menu(update, context)
        return
    if data == "menu:tasks":
        await tasks.show_menu(update, context)
        return
    if data == "menu:goals":
        await goals.show_menu(update, context)
        return
    if data == "menu:leaderboard":
        await reports.show_leaderboard_menu(update, context)
        return
    if data == "menu:reports":
        await reports.show_reports_menu(update, context)
        return
    if data == "menu:settings":
        await settings.show_menu(update, context)
        return

    if data.startswith("worship:"):
        handled = await worship.handle_callback(update, context, data)
        if handled:
            return
    if data.startswith("health:"):
        handled = await health.handle_callback(update, context, data)
        if handled:
            return
    if data.startswith("notes:"):
        handled = await notes.handle_callback(update, context, data)
        if handled:
            return
    if data.startswith("tasks:"):
        handled = await tasks.handle_callback(update, context, data)
        if handled:
            return
    if data.startswith("goals:"):
        handled = await goals.handle_callback(update, context, data)
        if handled:
            return
    if data.startswith("reports:") or data.startswith("leaderboard:"):
        handled = await reports.handle_callback(update, context, data)
        if handled:
            return
    if data.startswith("settings:"):
        handled = await settings.handle_callback(update, context, data)
        if handled:
            return

    await respond(update, "لم أفهم هذا الزر، حاول مرة أخرى.", reply_markup=main_menu_keyboard())


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_pending(context)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("حدث خطأ غير متوقع، حاول مرة أخرى.")
