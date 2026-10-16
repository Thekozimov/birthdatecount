import os
import aiosqlite
from datetime import datetime, timezone

class Database:
    def __init__(self, path):
        self.path = path

    async def init(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("""CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY, language TEXT NOT NULL DEFAULT 'uz',
                timezone TEXT NOT NULL DEFAULT 'Asia/Tashkent',
                created_at TEXT NOT NULL)""")
            await db.execute("""CREATE TABLE IF NOT EXISTS contacts(
                id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL,
                name TEXT NOT NULL, birthday TEXT, telegram_id INTEGER,
                notes TEXT DEFAULT '', created_at TEXT NOT NULL)""")
            await db.execute("""CREATE TABLE IF NOT EXISTS greetings(
                id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL,
                recipient_id INTEGER, recipient_name TEXT NOT NULL,
                message TEXT NOT NULL, send_at TEXT NOT NULL,
                media_type TEXT, media_id TEXT, recurring INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT, created_at TEXT NOT NULL)""")
            await db.execute("""CREATE TABLE IF NOT EXISTS reminders(
                id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL,
                contact_id INTEGER NOT NULL, remind_at TEXT NOT NULL,
                days_before INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL)""")
            await db.execute("""CREATE TABLE IF NOT EXISTS delivery_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT, greeting_id INTEGER,
                owner_id INTEGER NOT NULL, recipient_id INTEGER,
                result TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL)""")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_greetings_due ON greetings(status, send_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(status, remind_at)")
            await db.commit()

    async def execute(self, query, params=()):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(query, params)
            await db.commit()
            return cur

    async def fetchall(self, query, params=()):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(query, params)
            return await cur.fetchall()

    async def fetchone(self, query, params=()):
        rows = await self.fetchall(query, params)
        return rows[0] if rows else None

    async def upsert_user(self, user_id):
        now = datetime.now(timezone.utc).isoformat()
        await self.execute("INSERT OR IGNORE INTO users(user_id,created_at) VALUES(?,?)", (user_id, now))

    async def stats(self):
        queries = [
            ("users", "SELECT COUNT(*) n FROM users"),
            ("contacts", "SELECT COUNT(*) n FROM contacts"),
            ("pending", "SELECT COUNT(*) n FROM greetings WHERE status='pending'"),
            ("sent", "SELECT COUNT(*) n FROM greetings WHERE status='sent'"),
            ("failed", "SELECT COUNT(*) n FROM greetings WHERE status='failed'"),
        ]
        result = {}
        for key, q in queries:
            row = await self.fetchone(q)
            result[key] = row["n"]
        return result
