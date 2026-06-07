from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import Database
from bot.handlers.helpers import respond
from bot.keyboards.common import confirm_delete_keyboard, goal_actions_keyboard, goals_menu_keyboard, list_items_keyboard
from bot.utils.formatters import format_goal_details, format_list_items
from bot.utils.parsers import parse_int, split_pipe_text
from bot.utils.state import clear_pending, set_pending


def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.application.bot_data["db"]


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_pending(context)
    await respond(
        update,
        "🎯 قسم الأهداف\n\n"
        "تابع الأهداف الشخصية والمشتركة ونسبة الإنجاز بسهولة.",
        reply_markup=goals_menu_keyboard(),
    )


async def _show_goals_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = _db(context)
    goals = db.list_goals(update.effective_user.id)
    if not goals:
        await respond(update, "لا توجد أهداف بعد.", reply_markup=goals_menu_keyboard())
        return
    await respond(
        update,
        format_list_items("الأهداف", goals, empty_text="لا توجد أهداف بعد."),
        reply_markup=list_items_keyboard("goals", goals),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> bool:
    clear_pending(context)
    db = _db(context)
    user_id = update.effective_user.id

    if data == "goals:menu":
        await show_menu(update, context)
        return True
    if data in {"goals:list", "goals:progress_list"}:
        await _show_goals_list(update, context)
        return True

    if data in {"goals:add:personal", "goals:add:shared"}:
        shared = data.endswith("shared")
        set_pending(context, "goals:add", shared=shared)
        visibility = "مشترك" if shared else "شخصي"
        await respond(
            update,
            f"➕ أرسل الهدف {visibility} بهذا الشكل:\n\n`العنوان | الهدف الرقمي | الوصف`",
            reply_markup=goals_menu_keyboard(),
        )
        return True

    if data.startswith("goals:view:"):
        goal_id = int(data.split(":")[2])
        goal = db.get_goal(user_id, goal_id)
        if not goal:
            await respond(update, "الهدف غير موجود.", reply_markup=goals_menu_keyboard())
            return True
        await respond(update, format_goal_details(goal), reply_markup=goal_actions_keyboard(goal_id))
        return True

    if data.startswith("goals:progress:"):
        goal_id = int(data.split(":")[2])
        goal = db.get_goal(user_id, goal_id)
        if not goal:
            await respond(update, "الهدف غير موجود.", reply_markup=goals_menu_keyboard())
            return True
        set_pending(context, "goals:progress", goal_id=goal_id)
        await respond(
            update,
            "📈 أرسل مقدار الزيادة في التقدم.\n\nمثال: `5`",
            reply_markup=goals_menu_keyboard(),
        )
        return True

    if data.startswith("goals:edit:"):
        goal_id = int(data.split(":")[2])
        goal = db.get_goal(user_id, goal_id)
        if not goal:
            await respond(update, "الهدف غير موجود.", reply_markup=goals_menu_keyboard())
            return True
        set_pending(context, "goals:edit", goal_id=goal_id)
        await respond(
            update,
            "✏️ أرسل القيم الجديدة بهذا الشكل:\n\n`العنوان | الهدف الرقمي | الوصف`",
            reply_markup=goals_menu_keyboard(),
        )
        return True

    if data.startswith("goals:delete:"):
        goal_id = int(data.split(":")[2])
        goal = db.get_goal(user_id, goal_id)
        if not goal:
            await respond(update, "الهدف غير موجود.", reply_markup=goals_menu_keyboard())
            return True
        await respond(
            update,
            f"هل تريد حذف الهدف التالي؟\n\n{goal['title']}",
            reply_markup=confirm_delete_keyboard("goals", goal_id),
        )
        return True

    if data.startswith("goals:delete_confirm:"):
        goal_id = int(data.split(":")[2])
        deleted = db.delete_goal(user_id, goal_id)
        await respond(
            update,
            "🗑 تم حذف الهدف." if deleted else "تعذر حذف الهدف.",
            reply_markup=goals_menu_keyboard(),
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

    if action == "goals:add":
        parts = split_pipe_text(text, 3)
        title = parts[0]
        target_value = parse_int(parts[1], default=None, minimum=1)
        description = parts[2]
        if not title or target_value is None:
            await respond(
                update,
                "❗ استخدم الصيغة: `العنوان | الهدف الرقمي | الوصف`",
                reply_markup=goals_menu_keyboard(),
            )
            return True
        goal = db.add_goal(user_id, title, description, target_value, data.get("shared", False))
        clear_pending(context)
        await respond(
            update,
            f"✅ تم إضافة الهدف: {goal['title']}",
            reply_markup=goals_menu_keyboard(),
        )
        return True

    if action == "goals:edit":
        goal_id = int(data["goal_id"])
        parts = split_pipe_text(text, 3)
        title = parts[0]
        target_value = parse_int(parts[1], default=None, minimum=1)
        description = parts[2]
        if not title or target_value is None:
            await respond(
                update,
                "❗ استخدم الصيغة: `العنوان | الهدف الرقمي | الوصف`",
                reply_markup=goals_menu_keyboard(),
            )
            return True
        goal = db.update_goal(user_id, goal_id, title, description, target_value)
        clear_pending(context)
        await respond(
            update,
            f"✏️ تم تحديث الهدف: {goal['title'] if goal else title}",
            reply_markup=goals_menu_keyboard(),
        )
        return True

    if action == "goals:progress":
        goal_id = int(data["goal_id"])
        increment = parse_int(text, default=None, minimum=1)
        if increment is None:
            await respond(update, "❗ أرسل رقمًا صحيحًا.", reply_markup=goals_menu_keyboard())
            return True
        result = db.update_goal_progress(user_id, goal_id, increment)
        clear_pending(context)
        if not result["ok"]:
            await respond(update, "تعذر تحديث التقدم.", reply_markup=goals_menu_keyboard())
            return True
        goal = result["goal"]
        message = (
            f"📈 تم تحديث التقدم: {goal['current_value']}/{goal['target_value']}\n"
            f"نسبة الإنجاز: {int((goal['current_value'] / goal['target_value']) * 100) if goal['target_value'] else 0}%"
        )
        if result["completed"]:
            message += "\n🎉 تهانينا! تم إكمال الهدف."
        await respond(update, message, reply_markup=goals_menu_keyboard())
        return True

    return False
