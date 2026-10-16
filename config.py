import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/birthday_counter.db")
DEFAULT_TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")
POLL_SECONDS = max(10, int(os.getenv("POLL_SECONDS", "20")))
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
