from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import Database
from bot.handlers.helpers import respond
from bot.keyboards.common import confirm_delete_keyboard, item_actions_keyboard, list_items_keyboard, tasks_menu_keyboard
from bot.utils.formatters import format_list_items, format_task_details
from bot.utils.parsers import normalize_recurrence, parse_date, parse_int, parse_time, split_pipe_text
from bot.utils.state import clear_pending, set_pending


def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.application.bot_data["db"]


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_pending(context)
    await respond(
        update,
        "✅ قسم المهام\n\n"
        "أضف المهام، تابع التكرار اليومي أو الأسبوعي، واحصل على النقاط عند الإنجاز.",
        reply_markup=tasks_menu_keyboard(),
    )


async def _show_tasks_list(update: Update, context: ContextTypes.DEFAULT_TYPE, only_today: bool = False) -> None:
    db = _db(context)
    tasks = db.list_tasks(update.effective_user.id, include_completed=True)
    if only_today:
        tasks = db.due_tasks(update.effective_user.id)
    if not tasks:
        await respond(update, "لا توجد مهام بعد.", reply_markup=tasks_menu_keyboard())
        return
    await respond(
        update,
        format_list_items("المهام", tasks, empty_text="لا توجد مهام بعد."),
        reply_markup=list_items_keyboard("tasks", tasks, include_complete=True),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> bool:
    clear_pending(context)
    db = _db(context)
    user_id = update.effective_user.id

    if data == "tasks:menu":
        await show_menu(update, context)
        return True
    if data == "tasks:list":
        await _show_tasks_list(update, context)
        return True
    if data == "tasks:today":
        await _show_tasks_list(update, context, only_today=True)
        return True
    if data == "tasks:add":
        set_pending(context, "tasks:add")
        await respond(
            update,
            "➕ أرسل المهمة بهذا الشكل:\n\n"
            "`العنوان | YYYY-MM-DD أو - | مرة/يومية/أسبوعية | النقاط | HH:MM أو -`\n\n"
            "مثال: `قراءة سورة | 2026-06-10 | مرة | 25 | 19:00`",
            reply_markup=tasks_menu_keyboard(),
        )
        return True

    if data.startswith("tasks:view:"):
        task_id = int(data.split(":")[2])
        task = db.get_task(user_id, task_id)
        if not task:
            await respond(update, "المهمة غير موجودة.", reply_markup=tasks_menu_keyboard())
            return True
        await respond(
            update,
            format_task_details(task),
            reply_markup=item_actions_keyboard("tasks", task_id, include_complete=True),
        )
        return True

    if data.startswith("tasks:complete:"):
        task_id = int(data.split(":")[2])
        result = db.complete_task(user_id, task_id)
        if not result["ok"] and result["reason"] == "already_completed":
            await respond(update, "هذه المهمة مكتملة بالفعل.", reply_markup=tasks_menu_keyboard())
            return True
        if not result["ok"]:
            await respond(update, "تعذر إكمال المهمة.", reply_markup=tasks_menu_keyboard())
            return True
        task = result["task"]
        message = (
            f"✅ تم إكمال المهمة: {task['title']}\n"
            f"النقاط المكتسبة: {result['points']}\n"
            f"إجمالي المهام المنجزة: {result['user']['tasks_done_total']}"
        )
        if result["achievements"]:
            message += "\n\n🏆 إنجازات جديدة:\n" + "\n".join(
                f"{item['emoji']} {item['title']}" for item in result["achievements"]
            )
        await respond(update, message, reply_markup=tasks_menu_keyboard())
        return True

    if data.startswith("tasks:edit:"):
        task_id = int(data.split(":")[2])
        task = db.get_task(user_id, task_id)
        if not task:
            await respond(update, "المهمة غير موجودة.", reply_markup=tasks_menu_keyboard())
            return True
        set_pending(context, "tasks:edit", task_id=task_id)
        await respond(
            update,
            "✏️ أرسل القيم الجديدة بهذا الشكل:\n\n"
            "`العنوان | YYYY-MM-DD أو - | مرة/يومية/أسبوعية | النقاط | HH:MM أو -`",
            reply_markup=tasks_menu_keyboard(),
        )
        return True

    if data.startswith("tasks:delete:"):
        task_id = int(data.split(":")[2])
        task = db.get_task(user_id, task_id)
        if not task:
            await respond(update, "المهمة غير موجودة.", reply_markup=tasks_menu_keyboard())
            return True
        await respond(
            update,
            f"هل تريد حذف المهمة التالية؟\n\n{task['title']}",
            reply_markup=confirm_delete_keyboard("tasks", task_id),
        )
        return True

    if data.startswith("tasks:delete_confirm:"):
        task_id = int(data.split(":")[2])
        deleted = db.delete_task(user_id, task_id)
        await respond(
            update,
            "🗑 تم حذف المهمة." if deleted else "تعذر حذف المهمة.",
            reply_markup=tasks_menu_keyboard(),
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

    if action == "tasks:add":
        parts = split_pipe_text(text, 5)
        title = parts[0]
        due_date = parse_date(parts[1])
        recurrence = normalize_recurrence(parts[2])
        points = parse_int(parts[3], default=25, minimum=1) or 25
        remind_time = parse_time(parts[4])
        if not title:
            await respond(
                update,
                "❗ اكتب عنوان المهمة أولًا.\n\nمثال: `قراءة سورة | 2026-06-10 | مرة | 25 | 19:00`",
                reply_markup=tasks_menu_keyboard(),
            )
            return True
        task = db.add_task(user_id, title, due_date, recurrence, points, remind_time)
        clear_pending(context)
        await respond(update, f"✅ تمت إضافة المهمة: {task['title']}", reply_markup=tasks_menu_keyboard())
        return True

    if action == "tasks:edit":
        task_id = int(data["task_id"])
        parts = split_pipe_text(text, 5)
        title = parts[0]
        due_date = parse_date(parts[1])
        recurrence = normalize_recurrence(parts[2])
        points = parse_int(parts[3], default=25, minimum=1) or 25
        remind_time = parse_time(parts[4])
        if not title:
            await respond(
                update,
                "❗ اكتب عنوانًا صحيحًا للمهمة.",
                reply_markup=tasks_menu_keyboard(),
            )
            return True
        task = db.update_task(user_id, task_id, title, due_date, recurrence, points, remind_time)
        clear_pending(context)
        await respond(
            update,
            f"✏️ تم تحديث المهمة: {task['title'] if task else title}",
            reply_markup=tasks_menu_keyboard(),
        )
        return True

    return False
