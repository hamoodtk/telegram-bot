from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import (
    DAILY_REPORT_TIME,
    EVENING_ADHKAR_TIME,
    EXERCISE_REMINDER_TIME,
    FASTING_REMINDER_TIME,
    KAHF_REMINDER_TIME,
    MIDNIGHT_MAINTENANCE_TIME,
    MORNING_ADHKAR_TIME,
    PRAYER_TIMES,
    WEEKLY_REPORT_TIME,
)
from bot.handlers.helpers import respond
from bot.keyboards.common import settings_menu_keyboard
from bot.utils.state import clear_pending


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_pending(context)
    await respond(
        update,
        "⚙️ الإعدادات\n\n"
        "هنا يمكنك الاطلاع على جدول التذكيرات ومعلومات البوت.",
        reply_markup=settings_menu_keyboard(),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> bool:
    clear_pending(context)
    if data == "settings:schedule":
        lines = ["⏰ جدول التذكيرات", ""]
        for prayer_name, time_value in PRAYER_TIMES.items():
            lines.append(f"🕌 {prayer_name}: {time_value}")
        lines.extend(
            [
                f"🌅 أذكار الصباح: {MORNING_ADHKAR_TIME}",
                f"🌆 أذكار المساء: {EVENING_ADHKAR_TIME}",
                f"📖 الكهف: {KAHF_REMINDER_TIME} يوم الجمعة",
                f"🌙 الصيام: {FASTING_REMINDER_TIME} الاثنين والخميس",
                f"🏋️ الرياضة: {EXERCISE_REMINDER_TIME}",
                f"📊 التقرير اليومي: {DAILY_REPORT_TIME}",
                f"📆 التقرير الأسبوعي: {WEEKLY_REPORT_TIME}",
                f"🕐 صيانة منتصف الليل: {MIDNIGHT_MAINTENANCE_TIME}",
            ]
        )
        await respond(update, "\n".join(lines), reply_markup=settings_menu_keyboard())
        return True

    if data == "settings:about":
        await respond(
            update,
            "ℹ️ هذا بوت شخصي مغلق لشخصين فقط.\n\n"
            "تم بناؤه بـ Python و python-telegram-bot و APScheduler مع SQLite.",
            reply_markup=settings_menu_keyboard(),
        )
        return True

    return False
