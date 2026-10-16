import asyncio, logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter
from i18n import t

log=logging.getLogger(__name__)

async def scheduler_loop(bot: Bot, db, interval: int):
    while True:
        try:
            now=datetime.now(timezone.utc).isoformat()
            due=await db.fetchall("SELECT * FROM greetings WHERE status='pending' AND send_at<=? ORDER BY send_at LIMIT 50",(now,))
            for g in due:
                # Claim row before sending to reduce duplicate sends when restarted or concurrent workers.
                cur=await db.execute("UPDATE greetings SET status='sending' WHERE id=? AND status='pending'",(g["id"],))
                if not cur.rowcount: continue
                try:
                    body=f'🎂 <b>{escape(g["recipient_name"])}!</b>\n\n{escape(g["message"])}'
                    if g["media_type"]=="photo":
                        await bot.send_photo(g["recipient_id"],g["media_id"],caption=body)
                    elif g["media_type"]=="video":
                        await bot.send_video(g["recipient_id"],g["media_id"],caption=body)
                    elif g["media_type"]=="animation":
                        await bot.send_animation(g["recipient_id"],g["media_id"],caption=body)
                    else:
                        await bot.send_message(g["recipient_id"],body)
                    await db.execute("UPDATE greetings SET status='sent',last_error=NULL WHERE id=?",(g["id"],))
                    await db.execute("INSERT INTO delivery_log(greeting_id,owner_id,recipient_id,result,detail,created_at) VALUES(?,?,?,?,?,?)",
                        (g["id"],g["owner_id"],g["recipient_id"],"sent","OK",datetime.now(timezone.utc).isoformat()))
                    try: await bot.send_message(g["owner_id"],f'✅ #{g["id"]} tabrigi {escape(g["recipient_name"])} ga yuborildi.')
                    except Exception: pass
                    if g["recurring"]:
                        # Recurring greetings are advanced by one calendar year, with leap-day fallback.
                        from datetime import datetime as dt
                        old=dt.fromisoformat(g["send_at"])
                        try: nxt=old.replace(year=old.year+1)
                        except ValueError: nxt=old.replace(year=old.year+1,month=2,day=28)
                        await db.execute("UPDATE greetings SET status='pending',send_at=?,attempts=0 WHERE id=?",(nxt.isoformat(),g["id"]))
                except TelegramRetryAfter as e:
                    await db.execute("UPDATE greetings SET status='pending',attempts=attempts+1,last_error=? WHERE id=?",(f"Retry after {e.retry_after}",g["id"]))
                except (TelegramForbiddenError, TelegramBadRequest) as e:
                    attempts=g["attempts"]+1
                    status="failed" if attempts>=3 else "pending"
                    await db.execute("UPDATE greetings SET status=?,attempts=?,last_error=? WHERE id=?",(status,attempts,str(e)[:500],g["id"]))
                    await db.execute("INSERT INTO delivery_log(greeting_id,owner_id,recipient_id,result,detail,created_at) VALUES(?,?,?,?,?,?)",
                        (g["id"],g["owner_id"],g["recipient_id"],"failed",str(e)[:500],datetime.now(timezone.utc).isoformat()))
                    try: await bot.send_message(g["owner_id"],f'⚠️ #{g["id"]} tabrigini yuborib bo‘lmadi. Qabul qiluvchi /start qilganini va botni bloklamaganini tekshiring.')
                    except Exception: pass
                except Exception as e:
                    attempts=g["attempts"]+1
                    status="failed" if attempts>=5 else "pending"
                    await db.execute("UPDATE greetings SET status=?,attempts=?,last_error=? WHERE id=?",(status,attempts,str(e)[:500],g["id"]))
                    log.exception("Greeting %s failed",g["id"])
            await send_reminders(bot,db)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Scheduler loop error")
        await asyncio.sleep(interval)

async def send_reminders(bot,db):
    now=datetime.now(timezone.utc).isoformat()
    rows=await db.fetchall("""SELECT r.*,c.name,c.birthday FROM reminders r JOIN contacts c ON c.id=r.contact_id
        WHERE r.status='pending' AND r.remind_at<=? LIMIT 100""",(now,))
    for r in rows:
        cur=await db.execute("UPDATE reminders SET status='sending' WHERE id=? AND status='pending'",(r["id"],))
        if not cur.rowcount: continue
        try:
            await bot.send_message(r["owner_id"],f'🔔 Eslatma: {escape(r["name"])} ning tug‘ilgan kuniga {r["days_before"]} kun qoldi! 🎂')
            await db.execute("UPDATE reminders SET status='sent' WHERE id=?",(r["id"],))
        except Exception as e:
            await db.execute("UPDATE reminders SET status='failed' WHERE id=?",(r["id"],))
            log.warning("Reminder %s failed: %s",r["id"],e)

def escape(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
