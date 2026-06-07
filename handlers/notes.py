from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import Database
from bot.handlers.helpers import respond
from bot.keyboards.common import confirm_delete_keyboard, item_actions_keyboard, list_items_keyboard, notes_menu_keyboard
from bot.utils.formatters import format_list_items, format_note_details
from bot.utils.parsers import split_pipe_text
from bot.utils.state import clear_pending, set_pending


def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.application.bot_data["db"]


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_pending(context)
    await respond(
        update,
        "🗒 المفكرة\n\n"
        "احتفظ بملاحظاتك الخاصة المرتبطة بحسابك وحدك.",
        reply_markup=notes_menu_keyboard(),
    )


async def _show_notes_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = _db(context)
    notes = db.list_notes(update.effective_user.id)
    if not notes:
        await respond(update, "لا توجد ملاحظات بعد.", reply_markup=notes_menu_keyboard())
        return
    await respond(
        update,
        format_list_items("الملاحظات", notes, empty_text="لا توجد ملاحظات بعد."),
        reply_markup=list_items_keyboard("notes", notes),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> bool:
    clear_pending(context)
    db = _db(context)
    user_id = update.effective_user.id

    if data in {"notes:menu", "notes:list"}:
        if data == "notes:list":
            await _show_notes_list(update, context)
        else:
            await show_menu(update, context)
        return True

    if data == "notes:add":
        set_pending(context, "notes:add")
        await respond(
            update,
            "📝 أرسل الملاحظة بالشكل التالي:\n\n`العنوان | المحتوى`",
            reply_markup=notes_menu_keyboard(),
        )
        return True

    if data.startswith("notes:view:"):
        note_id = int(data.split(":")[2])
        note = db.get_note(user_id, note_id)
        if not note:
            await respond(update, "الملاحظة غير موجودة.", reply_markup=notes_menu_keyboard())
            return True
        await respond(update, format_note_details(note), reply_markup=item_actions_keyboard("notes", note_id))
        return True

    if data.startswith("notes:edit:"):
        note_id = int(data.split(":")[2])
        note = db.get_note(user_id, note_id)
        if not note:
            await respond(update, "الملاحظة غير موجودة.", reply_markup=notes_menu_keyboard())
            return True
        set_pending(context, "notes:edit", note_id=note_id)
        await respond(
            update,
            f"✏️ أرسل التعديل الجديد للملاحظة #{note_id} بالشكل التالي:\n\n`العنوان | المحتوى`",
            reply_markup=notes_menu_keyboard(),
        )
        return True

    if data.startswith("notes:delete:"):
        note_id = int(data.split(":")[2])
        note = db.get_note(user_id, note_id)
        if not note:
            await respond(update, "الملاحظة غير موجودة.", reply_markup=notes_menu_keyboard())
            return True
        await respond(
            update,
            f"هل تريد حذف الملاحظة التالية؟\n\n{note['title']}",
            reply_markup=confirm_delete_keyboard("notes", note_id),
        )
        return True

    if data.startswith("notes:delete_confirm:"):
        note_id = int(data.split(":")[2])
        deleted = db.delete_note(user_id, note_id)
        await respond(
            update,
            "🗑 تم حذف الملاحظة." if deleted else "تعذر حذف الملاحظة.",
            reply_markup=notes_menu_keyboard(),
        )
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

    if action == "notes:add":
        parts = split_pipe_text(text, 2)
        title = parts[0]
        content = parts[1]
        if not title or not content:
            await respond(
                update,
                "❗ استخدم الصيغة الصحيحة: `العنوان | المحتوى`",
                reply_markup=notes_menu_keyboard(),
            )
            return True
        note = db.add_note(user_id, title, content)
        clear_pending(context)
        await respond(update, f"✅ تمت إضافة الملاحظة: {note['title']}", reply_markup=notes_menu_keyboard())
        return True

    if action == "notes:edit":
        note_id = int(data["note_id"])
        parts = split_pipe_text(text, 2)
        title = parts[0]
        content = parts[1]
        if not title or not content:
            await respond(
                update,
                "❗ استخدم الصيغة الصحيحة: `العنوان | المحتوى`",
                reply_markup=notes_menu_keyboard(),
            )
            return True
        note = db.update_note(user_id, note_id, title, content)
        clear_pending(context)
        await respond(
            update,
            f"✏️ تم تحديث الملاحظة: {note['title'] if note else title}",
            reply_markup=notes_menu_keyboard(),
        )
        return True

    return False
