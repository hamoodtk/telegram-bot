from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import Database
from bot.handlers.helpers import respond
from bot.keyboards.common import prayer_keyboard, worship_menu_keyboard
from bot.utils.constants import QURAN_PAGE_PER_KHATMA
from bot.utils.formatters import format_quran_status
from bot.utils.parsers import parse_int, split_pipe_text
from bot.utils.state import clear_pending, set_pending


def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.application.bot_data["db"]


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📿 قسم العبادة\n\n"
        "سجّل عباداتك اليومية بسهولة، وتابع الصفحات والختمات والنقاط."
    )
    clear_pending(context)
    await respond(update, text, reply_markup=worship_menu_keyboard())


async def show_prayer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "🕌 اختر الصلاة التي أديتها الآن:"
    await respond(update, text, reply_markup=prayer_keyboard())


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> bool:
    clear_pending(context)
    db = _db(context)
    user_id = update.effective_user.id

    if data == "worship:prayer_menu":
        await show_prayer_menu(update, context)
        return True
    if data.startswith("worship:prayer:"):
        prayer_name = data.split(":", 2)[2]
        result = db.record_prayer(user_id, prayer_name)
        message = (
            f"✅ تم تسجيل صلاة {prayer_name}.\n"
            f"النقاط المكتسبة: {result['points']}\n"
            f"إجمالي صلواتك: {result['user']['prayer_total']}\n"
            f"السلسلة الحالية: {result['user']['current_streak']}"
        )
        if result["achievements"]:
            message += "\n\n🎉 إنجازات جديدة:\n" + "\n".join(
                f"{item['emoji']} {item['title']}" for item in result["achievements"]
            )
        await respond(update, message, reply_markup=prayer_keyboard())
        return True
    if data == "worship:morning_adhkar":
        result = db.record_adhkar(user_id, "morning")
        message = (
            "🌅 تم تسجيل أذكار الصباح.\n"
            f"النقاط المكتسبة: {result['points']}\n"
            f"السلسلة الحالية: {result['user']['current_streak']}"
        )
        if result["achievements"]:
            message += "\n\n🎉 إنجازات جديدة:\n" + "\n".join(
                f"{item['emoji']} {item['title']}" for item in result["achievements"]
            )
        await respond(update, message, reply_markup=worship_menu_keyboard())
        return True
    if data == "worship:evening_adhkar":
        result = db.record_adhkar(user_id, "evening")
        message = (
            "🌆 تم تسجيل أذكار المساء.\n"
            f"النقاط المكتسبة: {result['points']}\n"
            f"السلسلة الحالية: {result['user']['current_streak']}"
        )
        if result["achievements"]:
            message += "\n\n🎉 إنجازات جديدة:\n" + "\n".join(
                f"{item['emoji']} {item['title']}" for item in result["achievements"]
            )
        await respond(update, message, reply_markup=worship_menu_keyboard())
        return True
    if data == "worship:quran_pages":
        set_pending(context, "worship:quran_pages")
        await respond(
            update,
            "📖 أرسل عدد الصفحات المقروءة اليوم فقط.\n\nمثال: `10`\n\nيمكنك إرسال ملاحظة اختيارية بعد الرقم باستخدام |",
            reply_markup=worship_menu_keyboard(),
        )
        return True
    if data == "worship:quran_status":
        profile = db.get_user_profile(user_id)
        if not profile:
            await respond(update, "لا توجد بيانات بعد.", reply_markup=worship_menu_keyboard())
            return True
        await respond(
            update,
            format_quran_status(profile["quran_pages_total"], profile["quran_khatmas_total"]),
            reply_markup=worship_menu_keyboard(),
        )
        return True
    return False


async def process_pending(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    data: dict,
) -> bool:
    if action != "worship:quran_pages":
        return False

    db = _db(context)
    text = (update.message.text or "").strip()
    pieces = split_pipe_text(text, 2)
    pages = parse_int(pieces[0], default=None, minimum=1)
    note = pieces[1] or None
    if pages is None:
        await respond(
            update,
            "❗ أرسل رقمًا صحيحًا لعدد الصفحات.\n\nمثال: `10` أو `10 | قراءة بعد الفجر`",
            reply_markup=worship_menu_keyboard(),
        )
        return True

    result = db.record_quran_pages(update.effective_user.id, pages, note)
    clear_pending(context)
    message = (
        f"📖 تم تسجيل {pages} صفحة قرآن.\n"
        f"النقاط المكتسبة: {result['points']}\n"
        f"إجمالي الصفحات: {result['user']['quran_pages_total']}\n"
        f"إجمالي الختمات: {result['user']['quran_khatmas_total']}\n"
        f"الصفحات المتبقية للختمة التالية: {QURAN_PAGE_PER_KHATMA - (result['user']['quran_pages_total'] % QURAN_PAGE_PER_KHATMA) if result['user']['quran_pages_total'] % QURAN_PAGE_PER_KHATMA else 0}"
    )
    if result["bonus_khatmas"]:
        message += f"\n🎉 تمت إضافة {result['bonus_khatmas']} ختمة جديدة!"
    if result["achievements"]:
        message += "\n\n🏆 إنجازات جديدة:\n" + "\n".join(
            f"{item['emoji']} {item['title']}" for item in result["achievements"]
        )
    await respond(update, message, reply_markup=worship_menu_keyboard())
    return True
