import asyncio, logging, os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN, DATABASE_PATH, POLL_SECONDS, LOG_LEVEL
from db import Database
from handlers import router, set_db
from scheduler import scheduler_loop

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE":
        raise RuntimeError("BOT_TOKEN .env faylida sozlanmagan. .env.example faylini .env qilib nusxalang.")
    logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
                        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    db = Database(DATABASE_PATH)
    await db.init()
    set_db(db)
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    task = asyncio.create_task(scheduler_loop(bot, db, POLL_SECONDS))
    try:
        logging.info("Birthday Counter PRO MAX ishga tushdi")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        task.cancel()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
