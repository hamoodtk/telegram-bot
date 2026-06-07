from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import Database
from bot.handlers.helpers import respond
from bot.keyboards.common import leaderboard_menu_keyboard, reports_menu_keyboard
from bot.utils.formatters import (
    format_daily_report,
    format_leaderboard,
    format_profile_card,
    format_weekly_report,
)
from bot.utils.state import clear_pending


def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.application.bot_data["db"]


async def show_reports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_pending(context)
    await respond(
        update,
        "📊 قسم التقارير\n\n"
        "راجع أداء اليوم والأسبوع والترتيب العام بسرعة.",
        reply_markup=reports_menu_keyboard(),
    )


async def show_leaderboard_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_pending(context)
    await respond(
        update,
        "🏆 اختر نوع لوحة الترتيب:",
        reply_markup=leaderboard_menu_keyboard(),
    )


async def _send_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = _db(context)
    user_id = update.effective_user.id
    profile = db.get_user_profile(user_id)
    if not profile:
        await respond(update, "لا توجد بيانات بعد.", reply_markup=reports_menu_keyboard())
        return
    daily = db.get_daily_summary(user_id)
    report = {
        "display_name": profile["display_name"],
        "prayers_done": daily["prayers_done"],
        "quran_pages": daily["quran_pages"],
        "quran_khatmas": daily["quran_khatmas"],
        "exercises": daily["exercises"],
        "water_cups": daily["water_cups"],
        "points": daily["points"],
        "level_name": profile["level_name"],
        "effective_streak": daily["effective_streak"],
    }
    await respond(update, format_daily_report(report), reply_markup=reports_menu_keyboard())


async def _send_weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = _db(context)
    summary = db.get_weekly_summary(update.effective_user.id)
    await respond(update, format_weekly_report(summary), reply_markup=reports_menu_keyboard())


async def _send_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = _db(context)
    profile = db.get_user_profile(update.effective_user.id)
    if not profile:
        await respond(update, "لا توجد بيانات بعد.", reply_markup=reports_menu_keyboard())
        return
    await respond(update, format_profile_card(profile), reply_markup=reports_menu_keyboard())


async def _send_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str) -> None:
    db = _db(context)
    rows = db.get_leaderboard(period)
    title = "الترتيب الأسبوعي" if period == "week" else "الترتيب الشهري"
    await respond(update, format_leaderboard(title, rows), reply_markup=leaderboard_menu_keyboard())


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> bool:
    clear_pending(context)
    if data == "reports:daily":
        await _send_daily_report(update, context)
        return True
    if data == "reports:weekly":
        await _send_weekly_report(update, context)
        return True
    if data == "reports:leaderboard_week":
        await _send_leaderboard(update, context, "week")
        return True
    if data == "reports:leaderboard_month":
        await _send_leaderboard(update, context, "month")
        return True
    if data == "reports:profile":
        await _send_profile(update, context)
        return True
    if data == "leaderboard:week":
        await _send_leaderboard(update, context, "week")
        return True
    if data == "leaderboard:month":
        await _send_leaderboard(update, context, "month")
        return True
    return False
