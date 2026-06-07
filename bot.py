from __future__ import annotations

import logging

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.config import BOT_TOKEN, DATABASE_PATH, USER_IDS
from bot.database import Database
from bot.handlers import common
from bot.keyboards.common import main_reply_keyboard
from bot.scheduler.jobs import build_scheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def post_init(application) -> None:
    scheduler = build_scheduler(application)
    application.bot_data["scheduler"] = scheduler
    scheduler.start()
    await application.bot.set_my_commands(
        [
            ("start", "فتح البوت"),
            ("help", "مساعدة سريعة"),
            ("cancel", "إلغاء العملية الحالية"),
        ]
    )
    logger.info("Scheduler started")


async def post_shutdown(application) -> None:
    scheduler = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN غير مضبوط. أضفه في ملف .env أو كمتغير بيئة.")
    if not USER_IDS:
        raise SystemExit("USER_IDS غير مضبوط. أضف معرفي المستخدم المصرح لهما في ملف .env.")

    db = Database(DATABASE_PATH)
    db.initialize()

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    application.bot_data["db"] = db
    application.bot_data["reply_keyboard"] = main_reply_keyboard()

    application.add_handler(CommandHandler("start", common.start))
    application.add_handler(CommandHandler("help", common.help_command))
    application.add_handler(CommandHandler("cancel", common.cancel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, common.handle_text))
    application.add_handler(CallbackQueryHandler(common.handle_callback))
    application.add_error_handler(common.error_handler)

    logger.info("Bot is starting")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()

