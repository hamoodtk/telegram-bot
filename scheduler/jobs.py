from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from bot.config import (
    DAILY_REPORT_TIME,
    EVENING_ADHKAR_TIME,
    EXERCISE_REMINDER_TIME,
    FASTING_REMINDER_TIME,
    KAHF_REMINDER_TIME,
    MIDNIGHT_MAINTENANCE_TIME,
    MORNING_ADHKAR_TIME,
    PRAYER_TIMES,
    TIMEZONE,
    USER_IDS,
    WEEKLY_REPORT_TIME,
    WATER_REMINDER_HOURS,
)
from bot.keyboards.common import main_reply_keyboard
from bot.utils.formatters import (
    format_daily_report,
    format_leaderboard,
    format_weekly_report,
)


TZ = ZoneInfo(TIMEZONE)


async def _send_to_all(application, text: str, reply_markup=None) -> None:
    for user_id in USER_IDS:
        try:
            await application.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup or main_reply_keyboard(),
            )
        except Exception:
            continue


async def prayer_reminder_job(application, prayer_name: str) -> None:
    text = (
        f"🕌 تذكير الصلاة\n\n"
        f"حان الآن وقت صلاة {prayer_name}.\n"
        f"لا تنسَ الأجر العظيم، وبعدها سجّلها من البوت ✅"
    )
    await _send_to_all(application, text)


async def morning_adhkar_job(application) -> None:
    await _send_to_all(
        application,
        "🌅 تذكير أذكار الصباح\n\nابدأ يومك بالذكر والطمأنينة.",
    )


async def evening_adhkar_job(application) -> None:
    await _send_to_all(
        application,
        "🌆 تذكير أذكار المساء\n\nاختم يومك بالسكينة والاستغفار.",
    )


async def kahf_job(application) -> None:
    await _send_to_all(
        application,
        "📖 تذكير سورة الكهف\n\nاليوم الجمعة، لا تنسَ قراءة سورة الكهف.",
    )


async def fasting_job(application) -> None:
    await _send_to_all(
        application,
        "🌙 تذكير الصيام\n\nاليوم موعد صيام التطوع: الاثنين أو الخميس حسب الجدول.",
    )


async def exercise_job(application) -> None:
    await _send_to_all(
        application,
        "🏋️ تذكير الرياضة\n\nخصص اليوم وقتًا لحصة تمرين ولو كانت قصيرة.",
    )


async def water_job(application) -> None:
    await _send_to_all(
        application,
        "💧 تذكير الماء\n\nاشرب الآن كوبًا من الماء وابقَ ملتزمًا بالهدف اليومي.",
    )


async def task_reminder_job(application) -> None:
    db = application.bot_data["db"]
    for user_id in USER_IDS:
        tasks = db.get_today_task_summary(user_id)
        if not tasks:
            continue
        lines = ["✅ تذكير المهام", "", "المهام التي تحتاج متابعة:"]
        for task in tasks[:5]:
            lines.append(f"- {task['title']} ({task['recurrence']})")
        await application.bot.send_message(user_id, "\n".join(lines), reply_markup=main_reply_keyboard())


async def daily_report_job(application) -> None:
    db = application.bot_data["db"]
    for user_id in USER_IDS:
        profile = db.get_user_profile(user_id)
        if not profile:
            continue
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
        await application.bot.send_message(user_id, format_daily_report(report), reply_markup=main_reply_keyboard())


async def weekly_report_job(application) -> None:
    db = application.bot_data["db"]
    for user_id in USER_IDS:
        summary = db.get_weekly_summary(user_id)
        await application.bot.send_message(user_id, format_weekly_report(summary), reply_markup=main_reply_keyboard())


async def midnight_maintenance_job(application) -> None:
    db = application.bot_data["db"]
    db.reset_recurring_tasks()
    db.reset_inactive_streaks()


def build_scheduler(application) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TZ)

    for index, (prayer_name, time_value) in enumerate(PRAYER_TIMES.items(), start=1):
        hour, minute = [int(part) for part in time_value.split(":", 1)]
        scheduler.add_job(
            prayer_reminder_job,
            CronTrigger(hour=hour, minute=minute),
            args=[application, prayer_name],
            id=f"prayer_{index}",
            replace_existing=True,
        )

    morning_hour, morning_minute = [int(part) for part in MORNING_ADHKAR_TIME.split(":", 1)]
    evening_hour, evening_minute = [int(part) for part in EVENING_ADHKAR_TIME.split(":", 1)]
    kahf_hour, kahf_minute = [int(part) for part in KAHF_REMINDER_TIME.split(":", 1)]
    fasting_hour, fasting_minute = [int(part) for part in FASTING_REMINDER_TIME.split(":", 1)]
    exercise_hour, exercise_minute = [int(part) for part in EXERCISE_REMINDER_TIME.split(":", 1)]
    daily_hour, daily_minute = [int(part) for part in DAILY_REPORT_TIME.split(":", 1)]
    weekly_hour, weekly_minute = [int(part) for part in WEEKLY_REPORT_TIME.split(":", 1)]
    midnight_hour, midnight_minute = [int(part) for part in MIDNIGHT_MAINTENANCE_TIME.split(":", 1)]

    scheduler.add_job(
        morning_adhkar_job,
        CronTrigger(hour=morning_hour, minute=morning_minute),
        args=[application],
        id="morning_adhkar",
        replace_existing=True,
    )
    scheduler.add_job(
        evening_adhkar_job,
        CronTrigger(hour=evening_hour, minute=evening_minute),
        args=[application],
        id="evening_adhkar",
        replace_existing=True,
    )
    scheduler.add_job(
        kahf_job,
        CronTrigger(day_of_week="fri", hour=kahf_hour, minute=kahf_minute),
        args=[application],
        id="kahf_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        fasting_job,
        CronTrigger(day_of_week="mon,thu", hour=fasting_hour, minute=fasting_minute),
        args=[application],
        id="fasting_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        exercise_job,
        CronTrigger(hour=exercise_hour, minute=exercise_minute),
        args=[application],
        id="exercise_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        water_job,
        CronTrigger(hour=",".join(str(hour) for hour in WATER_REMINDER_HOURS), minute=0),
        args=[application],
        id="water_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        task_reminder_job,
        CronTrigger(hour="9-21/3", minute=0),
        args=[application],
        id="task_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        daily_report_job,
        CronTrigger(hour=daily_hour, minute=daily_minute),
        args=[application],
        id="daily_report",
        replace_existing=True,
    )
    scheduler.add_job(
        weekly_report_job,
        CronTrigger(day_of_week="sun", hour=weekly_hour, minute=weekly_minute),
        args=[application],
        id="weekly_report",
        replace_existing=True,
    )
    scheduler.add_job(
        midnight_maintenance_job,
        CronTrigger(hour=midnight_hour, minute=midnight_minute),
        args=[application],
        id="midnight_maintenance",
        replace_existing=True,
    )

    return scheduler
