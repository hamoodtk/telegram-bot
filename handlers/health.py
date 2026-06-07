from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import Database
from bot.handlers.helpers import respond
from bot.keyboards.common import health_menu_keyboard
from bot.utils.formatters import format_weight_history
from bot.utils.parsers import parse_float, parse_int, split_pipe_text
from bot.utils.state import clear_pending, set_pending


def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.application.bot_data["db"]


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_pending(context)
    await respond(
        update,
        "🏋️ قسم الرياضة والصحة\n\n"
        "تابع التمارين والوزن والماء بسهولة ومن مكان واحد.",
        reply_markup=health_menu_keyboard(),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> bool:
    clear_pending(context)
    db = _db(context)
    user_id = update.effective_user.id

    if data == "health:exercise":
        set_pending(context, "health:exercise")
        await respond(
            update,
            "🏃 أرسل وصف التمرين بشكل بسيط، ويمكنك إضافة الدقائق بعد |.\n\nمثال: `مشي سريع | 30`",
            reply_markup=health_menu_keyboard(),
        )
        return True

    if data == "health:weight":
        set_pending(context, "health:weight")
        await respond(
            update,
            "⚖️ أرسل الوزن بالكيلو، ويمكن إضافة ملاحظة اختيارية بعد |.\n\nمثال: `72.5 | بعد التمرين`",
            reply_markup=health_menu_keyboard(),
        )
        return True

    if data == "health:water":
        set_pending(context, "health:water")
        await respond(
            update,
            "💧 أرسل عدد الأكواب التي شربتها الآن.\n\nمثال: `2`",
            reply_markup=health_menu_keyboard(),
        )
        return True

    if data == "health:weight_history":
        rows = db.weight_history(user_id, limit=10)
        await respond(update, format_weight_history(rows), reply_markup=health_menu_keyboard())
        return True

    if data == "health:water_count":
        profile = db.get_user_profile(user_id)
        today = db.get_daily_summary(user_id)
        text = (
            "🥤 عداد الماء اليوم\n\n"
            f"المسجل اليوم: {today['water_cups']} كوب\n"
            "الهدف اليومي المقترح: 8 أكواب\n"
            f"إجمالي أكواب الماء المسجلة: {profile['water_cups_total'] if profile else 0}"
        )
        await respond(update, text, reply_markup=health_menu_keyboard())
        return True

    return False


async def process_pending(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    data: dict,
) -> bool:
    db = _db(context)
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    if action == "health:exercise":
        parts = split_pipe_text(text, 2)
        description = parts[0]
        minutes = parse_int(parts[1], default=None, minimum=1) if len(parts) > 1 else None
        if not description:
            await respond(
                update,
                "❗ اكتب وصفًا مناسبًا للتمرين.\n\nمثال: `مشي سريع | 30`",
                reply_markup=health_menu_keyboard(),
            )
            return True
        result = db.record_exercise(user_id, description, minutes)
        clear_pending(context)
        message = (
            f"✅ تم تسجيل التمرين: {description}\n"
            f"النقاط المكتسبة: {result['points']}\n"
            f"إجمالي التمارين: {result['user']['exercise_total']}"
        )
        if result["achievements"]:
            message += "\n\n🏆 إنجازات جديدة:\n" + "\n".join(
                f"{item['emoji']} {item['title']}" for item in result["achievements"]
            )
        await respond(update, message, reply_markup=health_menu_keyboard())
        return True

    if action == "health:weight":
        parts = split_pipe_text(text, 2)
        weight = parse_float(parts[0], default=None, minimum=1.0)
        note = parts[1] or None
        if weight is None:
            await respond(
                update,
                "❗ أرسل وزنًا صحيحًا.\n\nمثال: `72.5 | بعد التمرين`",
                reply_markup=health_menu_keyboard(),
            )
            return True
        result = db.record_weight(user_id, weight, note)
        clear_pending(context)
        await respond(
            update,
            f"⚖️ تم تسجيل الوزن: {weight:.1f} كغ\n"
            f"الوقت: {result['measured_at'][:19].replace('T', ' ')}",
            reply_markup=health_menu_keyboard(),
        )
        return True

    if action == "health:water":
        cups = parse_int(text, default=None, minimum=1)
        if cups is None:
            await respond(
                update,
                "❗ أرسل عددًا صحيحًا للأكواب.\n\nمثال: `2`",
                reply_markup=health_menu_keyboard(),
            )
            return True
        result = db.record_water(user_id, cups)
        clear_pending(context)
        message = (
            f"💧 تم تسجيل {cups} كوب ماء.\n"
            f"النقاط المكتسبة: {result['points']}\n"
            f"إجمالي الماء اليوم: {result['daily']['water_cups']} كوب\n"
            f"السلسلة الحالية: {result['user']['current_streak']}"
        )
        if result["achievements"]:
            message += "\n\n🏆 إنجازات جديدة:\n" + "\n".join(
                f"{item['emoji']} {item['title']}" for item in result["achievements"]
            )
        await respond(update, message, reply_markup=health_menu_keyboard())
        return True

    return False
