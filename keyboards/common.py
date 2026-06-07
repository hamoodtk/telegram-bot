from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.utils.constants import BACK_LABEL, CANCEL_LABEL, HOME_LABEL, MAIN_MENU_LABELS, REFRESH_LABEL, PRAYERS


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(MAIN_MENU_LABELS["worship"]), KeyboardButton(MAIN_MENU_LABELS["health"])],
            [KeyboardButton(MAIN_MENU_LABELS["notes"]), KeyboardButton(MAIN_MENU_LABELS["tasks"])],
            [KeyboardButton(MAIN_MENU_LABELS["goals"]), KeyboardButton(MAIN_MENU_LABELS["leaderboard"])],
            [KeyboardButton(MAIN_MENU_LABELS["reports"]), KeyboardButton(MAIN_MENU_LABELS["settings"])],
            [KeyboardButton(HOME_LABEL), KeyboardButton(REFRESH_LABEL), KeyboardButton(CANCEL_LABEL)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def back_to_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="menu:home")]]
    )


def simple_back_keyboard(callback_data: str = "menu:home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=callback_data)]])


def confirm_keyboard(yes_callback: str, no_callback: str = "menu:home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ نعم", callback_data=yes_callback),
                InlineKeyboardButton("↩️ لا", callback_data=no_callback),
            ]
        ]
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📿 العبادة", callback_data="menu:worship"), InlineKeyboardButton("🏋️ الرياضة", callback_data="menu:health")],
            [InlineKeyboardButton("🗒 المفكرة", callback_data="menu:notes"), InlineKeyboardButton("✅ المهام", callback_data="menu:tasks")],
            [InlineKeyboardButton("🎯 الأهداف", callback_data="menu:goals"), InlineKeyboardButton("🏆 الترتيب", callback_data="menu:leaderboard")],
            [InlineKeyboardButton("📊 التقارير", callback_data="menu:reports"), InlineKeyboardButton("⚙️ الإعدادات", callback_data="menu:settings")],
        ]
    )


def worship_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🕌 تسجيل صلاة", callback_data="worship:prayer_menu")],
            [InlineKeyboardButton("🌅 أذكار الصباح", callback_data="worship:morning_adhkar"), InlineKeyboardButton("🌆 أذكار المساء", callback_data="worship:evening_adhkar")],
            [InlineKeyboardButton("📖 قراءة القرآن", callback_data="worship:quran_pages"), InlineKeyboardButton("📚 حالة القرآن", callback_data="worship:quran_status")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu:home")],
        ]
    )


def prayer_keyboard() -> InlineKeyboardMarkup:
    rows = []
    current_row = []
    for index, prayer in enumerate(PRAYERS, start=1):
        current_row.append(InlineKeyboardButton(f"✅ {prayer}", callback_data=f"worship:prayer:{prayer}"))
        if index % 2 == 0:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu:worship")])
    return InlineKeyboardMarkup(rows)


def health_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🏃 تسجيل تمرين", callback_data="health:exercise"), InlineKeyboardButton("⚖️ تسجيل وزن", callback_data="health:weight")],
            [InlineKeyboardButton("💧 شرب ماء", callback_data="health:water"), InlineKeyboardButton("📈 تطور الوزن", callback_data="health:weight_history")],
            [InlineKeyboardButton("🥤 عداد الماء", callback_data="health:water_count"), InlineKeyboardButton("🔙 رجوع", callback_data="menu:home")],
        ]
    )


def notes_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ إضافة ملاحظة", callback_data="notes:add"), InlineKeyboardButton("📂 عرض الملاحظات", callback_data="notes:list")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu:home")],
        ]
    )


def tasks_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ إضافة مهمة", callback_data="tasks:add"), InlineKeyboardButton("📂 عرض المهام", callback_data="tasks:list")],
            [InlineKeyboardButton("⏰ مهامي اليوم", callback_data="tasks:today"), InlineKeyboardButton("🔙 رجوع", callback_data="menu:home")],
        ]
    )


def goals_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ هدف شخصي", callback_data="goals:add:personal"), InlineKeyboardButton("🤝 هدف مشترك", callback_data="goals:add:shared")],
            [InlineKeyboardButton("📂 عرض الأهداف", callback_data="goals:list"), InlineKeyboardButton("📈 متابعة التقدم", callback_data="goals:progress_list")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu:home")],
        ]
    )


def leaderboard_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📆 أسبوعي", callback_data="leaderboard:week"), InlineKeyboardButton("🗓 شهري", callback_data="leaderboard:month")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu:home")],
        ]
    )


def reports_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📊 تقرير اليوم", callback_data="reports:daily"), InlineKeyboardButton("📆 تقرير الأسبوع", callback_data="reports:weekly")],
            [InlineKeyboardButton("🏆 الترتيب الأسبوعي", callback_data="reports:leaderboard_week"), InlineKeyboardButton("🏅 الترتيب الشهري", callback_data="reports:leaderboard_month")],
            [InlineKeyboardButton("👤 ملفي", callback_data="reports:profile"), InlineKeyboardButton("🔙 رجوع", callback_data="menu:home")],
        ]
    )


def settings_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⏰ جدول التذكيرات", callback_data="settings:schedule"), InlineKeyboardButton("ℹ️ حول البوت", callback_data="settings:about")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu:home")],
        ]
    )


def item_actions_keyboard(prefix: str, item_id: int, include_complete: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    if include_complete:
        row.append(InlineKeyboardButton("✅ تم", callback_data=f"{prefix}:complete:{item_id}"))
    row.append(InlineKeyboardButton("✏️ تعديل", callback_data=f"{prefix}:edit:{item_id}"))
    row.append(InlineKeyboardButton("🗑 حذف", callback_data=f"{prefix}:delete:{item_id}"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"{prefix}:list")])
    return InlineKeyboardMarkup(buttons)


def confirm_delete_keyboard(prefix: str, item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🗑 نعم احذف", callback_data=f"{prefix}:delete_confirm:{item_id}"),
                InlineKeyboardButton("↩️ إلغاء", callback_data=f"{prefix}:list"),
            ],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="menu:home")],
        ]
    )


def list_items_keyboard(prefix: str, rows: list[dict], title_key: str = "title", include_complete: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    for row in rows:
        label = row.get(title_key, "عنصر")
        status = "✅" if include_complete and int(row.get("is_completed") or 0) else "📌"
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{status} {label[:24]}",
                    callback_data=f"{prefix}:view:{row['id']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"{prefix}:menu")])
    return InlineKeyboardMarkup(buttons)


def goal_actions_keyboard(goal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ تقدم", callback_data=f"goals:progress:{goal_id}"),
                InlineKeyboardButton("✏️ تعديل", callback_data=f"goals:edit:{goal_id}"),
            ],
            [
                InlineKeyboardButton("🗑 حذف", callback_data=f"goals:delete:{goal_id}"),
                InlineKeyboardButton("🔙 رجوع", callback_data="goals:list"),
            ],
        ]
    )

