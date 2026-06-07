from __future__ import annotations

from datetime import date
from typing import Iterable

from bot.utils.constants import ACHIEVEMENTS, LEVELS, QURAN_PAGE_PER_KHATMA
from bot.utils.parsers import clamp_text


def progress_bar(current: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "░" * width
    ratio = max(0.0, min(1.0, current / total))
    filled = round(width * ratio)
    return "█" * filled + "░" * (width - filled)


def format_points(value: int) -> str:
    return f"{value:,}".replace(",", "،")


def level_from_points(points: int) -> dict:
    selected = LEVELS[0]
    next_threshold = None
    for index, level in enumerate(LEVELS):
        selected = level
        if index + 1 < len(LEVELS):
            next_threshold = LEVELS[index + 1][0]
        if points < level[0]:
            break
        if index + 1 == len(LEVELS) or points < LEVELS[index + 1][0]:
            break

    current_threshold, level_name = selected
    if points < LEVELS[0][0]:
        current_threshold, level_name = LEVELS[0]
    if next_threshold is None:
        next_threshold = current_threshold
    if points >= LEVELS[-1][0]:
        return {
            "name": LEVELS[-1][1],
            "current_threshold": LEVELS[-1][0],
            "next_threshold": LEVELS[-1][0],
            "next_name": LEVELS[-1][1],
            "progress": 100,
        }

    next_level = next((lvl for lvl in LEVELS if lvl[0] > points), LEVELS[-1])
    start_threshold = current_threshold
    end_threshold = next_level[0]
    span = max(1, end_threshold - start_threshold)
    progress = int(((points - start_threshold) / span) * 100)

    return {
        "name": level_name,
        "current_threshold": start_threshold,
        "next_threshold": end_threshold,
        "next_name": next_level[1],
        "progress": max(0, min(100, progress)),
    }


def format_level_summary(points: int) -> str:
    level = level_from_points(points)
    return (
        f"🏅 المستوى: {level['name']}\n"
        f"📈 التقدم نحو {level['next_name']}: {progress_bar(level['progress'], 100)} {level['progress']}%"
    )


def format_profile_card(profile: dict) -> str:
    level = level_from_points(profile["total_points"])
    today_active = profile.get("today_activity", 0)
    today_points = profile.get("today_points", 0)
    last_weight = profile.get("last_weight")
    weight_line = f"{last_weight:.1f} كغ" if isinstance(last_weight, (int, float)) else "لا يوجد"

    return (
        f"👤 الملف الشخصي\n\n"
        f"الاسم: {profile['display_name']}\n"
        f"النقاط: {format_points(profile['total_points'])}\n"
        f"المستوى: {level['name']}\n"
        f"السلسلة الحالية: {profile['effective_streak']}\n"
        f"أفضل سلسلة: {profile['best_streak']}\n"
        f"النقاط اليوم: {format_points(today_points)}\n"
        f"النشاط اليوم: {today_active}\n\n"
        f"القرآن: {format_points(profile['quran_pages_total'])} صفحة\n"
        f"الختمات: {format_points(profile['quran_khatmas_total'])}\n"
        f"الصلوات: {format_points(profile['prayer_total'])}\n"
        f"الأذكار: {format_points(profile['morning_adhkar_total'] + profile['evening_adhkar_total'])}\n"
        f"التمارين: {format_points(profile['exercise_total'])}\n"
        f"الماء: {format_points(profile['water_cups_total'])} كوب\n"
        f"آخر وزن: {weight_line}\n\n"
        f"{level['name']} · {progress_bar(level['progress'], 100)} {level['progress']}%"
    )


def format_daily_report(report: dict) -> str:
    return (
        f"📊 التقرير اليومي\n\n"
        f"الاسم: {report['display_name']}\n"
        f"الصلوات: {report['prayers_done']}\n"
        f"القرآن: {report['quran_pages']} صفحة\n"
        f"الختمات: {report['quran_khatmas']}\n"
        f"التمارين: {report['exercises']}\n"
        f"الماء: {report['water_cups']} كوب\n"
        f"النقاط: {format_points(report['points'])}\n"
        f"المستوى: {report['level_name']}\n"
        f"السلسلة: {report['effective_streak']}"
    )


def format_weekly_report(report: dict) -> str:
    return (
        f"📆 التقرير الأسبوعي\n\n"
        f"إجمالي النقاط: {format_points(report['points'])}\n"
        f"عدد التمارين: {report['exercises']}\n"
        f"صفحات القرآن: {report['quran_pages']}\n"
        f"نسبة الالتزام: {report['adherence']}%\n"
        f"أيام النشاط: {report['active_days']}/7\n"
        f"السلسلة الحالية: {report['effective_streak']}\n"
        f"المستوى: {report['level_name']}"
    )


def format_leaderboard(title: str, rows: list[dict]) -> str:
    lines = [f"🏆 {title}"]
    if not rows:
        lines.append("\nلا توجد بيانات بعد.")
        return "\n".join(lines)

    medals = ["🥇", "🥈", "🥉"]
    for index, row in enumerate(rows, start=1):
        medal = medals[index - 1] if index <= len(medals) else f"{index}."
        name = row.get("display_name") or row.get("first_name") or f"المستخدم {row['telegram_id']}"
        lines.append(f"{medal} {name} — {format_points(row['points'])} نقطة")
    return "\n".join(lines)


def format_list_items(title: str, rows: Iterable[dict], empty_text: str = "لا توجد عناصر.") -> str:
    lines = [f"🗂 {title}"]
    rows = list(rows)
    if not rows:
        lines.append(f"\n{empty_text}")
        return "\n".join(lines)

    for index, row in enumerate(rows, start=1):
        lines.append(f"{index}. {clamp_text(row.get('title', ''))}")
    return "\n".join(lines)


def format_note_details(note: dict) -> str:
    return (
        f"📝 ملاحظة\n\n"
        f"العنوان: {note['title']}\n"
        f"المحتوى:\n{note['content']}\n\n"
        f"آخر تعديل: {note['updated_at']}"
    )


def format_task_details(task: dict) -> str:
    status = "✅ مكتملة" if task["is_completed"] else "⏳ قيد التنفيذ"
    recurrence = {"once": "مرة واحدة", "daily": "يومية", "weekly": "أسبوعية"}.get(task["recurrence"], "مرة واحدة")
    return (
        f"✅ مهمة\n\n"
        f"العنوان: {task['title']}\n"
        f"التكرار: {recurrence}\n"
        f"التاريخ: {task['due_date'] or 'غير محدد'}\n"
        f"الوقت: {task['remind_time'] or 'غير محدد'}\n"
        f"النقاط: {task['points']}\n"
        f"الحالة: {status}\n"
        f"آخر تحديث: {task['updated_at']}"
    )


def format_goal_details(goal: dict) -> str:
    percent = 0
    if goal["target_value"] > 0:
        percent = int(min(100, (goal["current_value"] / goal["target_value"]) * 100))
    visibility = "مشترك" if goal["shared"] else "شخصي"
    return (
        f"🎯 هدف {visibility}\n\n"
        f"العنوان: {goal['title']}\n"
        f"الوصف: {goal['description'] or 'لا يوجد'}\n"
        f"التقدم: {goal['current_value']}/{goal['target_value']} ({percent}%)\n"
        f"{progress_bar(percent, 100)}\n"
        f"آخر تحديث: {goal['updated_at']}"
    )


def format_weight_history(rows: list[dict]) -> str:
    lines = ["⚖️ *تطور الوزن*"]
    if not rows:
        lines.append("\nلا توجد قياسات بعد.")
        return "\n".join(lines)

    previous = None
    for row in rows:
        weight = float(row["weight"])
        delta = ""
        if previous is not None:
            change = weight - previous
            if change > 0:
                delta = f" (+{change:.1f})"
            elif change < 0:
                delta = f" ({change:.1f})"
        previous = weight
        lines.append(f"- {row['measured_at'][:10]}: {weight:.1f} كغ{delta}")
    return "\n".join(lines)


def format_quran_status(total_pages: int, total_khatmas: int) -> str:
    pages_left = QURAN_PAGE_PER_KHATMA - (total_pages % QURAN_PAGE_PER_KHATMA)
    if pages_left == QURAN_PAGE_PER_KHATMA and total_pages > 0:
        pages_left = 0
    return (
        f"📖 حالة القرآن\n\n"
        f"إجمالي الصفحات: {format_points(total_pages)}\n"
        f"إجمالي الختمات: {format_points(total_khatmas)}\n"
        f"الصفحات المتبقية للختمة التالية: {pages_left}"
    )
