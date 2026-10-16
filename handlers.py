import csv, io, logging
from datetime import datetime, date, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from db import Database
from i18n import t

router = Router()
DB: Database | None = None
def set_db(db): 
    global DB
    DB = db

class ContactFlow(StatesGroup):
    name = State(); birthday = State(); telegram_id = State(); notes = State()

class GreetingFlow(StatesGroup):
    recipient_id = State(); recipient_name = State(); message = State(); send_at = State(); media = State()

def menu(lang):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t(lang,"contacts")), KeyboardButton(text=t(lang,"add_contact"))],
        [KeyboardButton(text=t(lang,"birthdays")), KeyboardButton(text=t(lang,"schedule"))],
        [KeyboardButton(text=t(lang,"greetings")), KeyboardButton(text=t(lang,"reminders"))],
        [KeyboardButton(text=t(lang,"stats")), KeyboardButton(text=t(lang,"export"))],
        [KeyboardButton(text=t(lang,"settings")), KeyboardButton(text=t(lang,"help"))]
    ], resize_keyboard=True)

async def lang_of(uid):
    row = await DB.fetchone("SELECT language FROM users WHERE user_id=?", (uid,))
    return row["language"] if row else "uz"

async def ensure(message):
    await DB.upsert_user(message.from_user.id)
    return await lang_of(message.from_user.id)

async def start_contact(message, state, lang):
    await state.clear(); await state.set_state(ContactFlow.name)
    await message.answer(t(lang,"ask_contact")+"\n"+t(lang,"cancel_hint"))

async def start_greeting(message, state, lang):
    await state.clear(); await state.set_state(GreetingFlow.recipient_id)
    await message.answer(t(lang,"ask_recipient")+"\n"+t(lang,"cancel_hint"))

@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    lang = await ensure(m)
    await state.clear()
    await m.answer(t(lang,"welcome")+"\n\n"+t(lang,"menu"), reply_markup=menu(lang))

@router.message(Command("help"))
@router.message(F.text.in_({"ℹ️ Yordam","ℹ️ Помощь","ℹ️ Help"}))
async def help_cmd(m: Message):
    lang = await ensure(m); await m.answer(t(lang,"help_text"))

@router.message(Command("cancel"))
async def cancel(m: Message, state: FSMContext):
    lang = await ensure(m); await state.clear()
    await m.answer(t(lang,"cancel"), reply_markup=menu(lang))

@router.message(Command("language"))
@router.message(F.text.in_({"⚙️ Sozlamalar","⚙️ Настройки","⚙️ Settings"}))
async def language(m: Message):
    lang = await ensure(m)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O‘zbekcha", callback_data="lang:uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")]])
    await m.answer(t(lang,"choose_lang"), reply_markup=kb)

@router.callback_query(F.data.startswith("lang:"))
async def language_set(c: CallbackQuery):
    lang = c.data.split(":")[1]
    if lang not in {"uz","ru","en"}: return await c.answer()
    await DB.execute("UPDATE users SET language=? WHERE user_id=?", (lang,c.from_user.id))
    await c.message.edit_text(t(lang,"lang_saved"))
    await c.message.answer(t(lang,"menu"), reply_markup=menu(lang))
    await c.answer()

@router.message(Command("addcontact"))
@router.message(F.text.in_({"➕ Kontakt qo‘shish","➕ Добавить контакт","➕ Add contact"}))
async def add_contact(m: Message, state: FSMContext):
    lang = await ensure(m); await start_contact(m,state,lang)

@router.message(ContactFlow.name)
async def contact_name(m: Message, state: FSMContext):
    lang = await lang_of(m.from_user.id)
    name = (m.text or "").strip()
    if not name or len(name)>100: return await m.answer("Ism 1–100 belgi bo‘lishi kerak.")
    await state.update_data(name=name); await state.set_state(ContactFlow.birthday)
    await m.answer(t(lang,"ask_birthday"))

@router.message(ContactFlow.birthday)
async def contact_birthday(m: Message, state: FSMContext):
    lang = await lang_of(m.from_user.id); value=(m.text or "").strip()
    birthday = None
    if value.lower() != "/skip":
        try:
            parsed=date.fromisoformat(value)
            if parsed.year < 1900: raise ValueError()
            birthday=parsed.isoformat()
        except ValueError: return await m.answer(t(lang,"bad_date"))
    await state.update_data(birthday=birthday); await state.set_state(ContactFlow.telegram_id)
    await m.answer(t(lang,"ask_tg"))

@router.message(ContactFlow.telegram_id)
async def contact_tg(m: Message, state: FSMContext):
    lang=await lang_of(m.from_user.id); val=(m.text or "").strip(); tg=None
    if val.lower()!="/skip":
        if not val.isdigit(): return await m.answer("Telegram ID raqam bo‘lishi kerak yoki /skip.")
        tg=int(val)
    await state.update_data(telegram_id=tg); await state.set_state(ContactFlow.notes)
    await m.answer(t(lang,"ask_notes"))

@router.message(ContactFlow.notes)
async def contact_notes(m: Message, state: FSMContext):
    lang=await lang_of(m.from_user.id); data=await state.get_data()
    notes="" if (m.text or "").strip().lower()=="/skip" else (m.text or "")[:500]
    await DB.execute("INSERT INTO contacts(owner_id,name,birthday,telegram_id,notes,created_at) VALUES(?,?,?,?,?,?)",
        (m.from_user.id,data["name"],data["birthday"],data["telegram_id"],notes,datetime.utcnow().isoformat()))
    await state.clear(); await m.answer(t(lang,"saved"), reply_markup=menu(lang))

@router.message(Command("contacts"))
@router.message(F.text.in_({"📇 Kontaktlar","📇 Контакты","📇 Contacts"}))
async def contacts(m: Message):
    lang=await ensure(m)
    rows=await DB.fetchall("SELECT * FROM contacts WHERE owner_id=? ORDER BY name COLLATE NOCASE",(m.from_user.id,))
    if not rows: return await m.answer(t(lang,"no_items"))
    lines=["<b>"+t(lang,"contacts")+"</b>"]
    for r in rows:
        lines.append(f'#{r["id"]} · {esc(r["name"])}'+(f' — {r["birthday"]}' if r["birthday"] else '')+(f' · ID {r["telegram_id"]}' if r["telegram_id"] else ''))
    lines.append("\nO‘chirish: /deletecontact ID")
    await m.answer("\n".join(lines))

def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

@router.message(Command("deletecontact"))
async def delete_contact(m: Message):
    lang=await ensure(m); parts=(m.text or "").split()
    if len(parts)!=2 or not parts[1].isdigit(): return await m.answer("Foydalanish: /deletecontact ID")
    cur=await DB.execute("DELETE FROM contacts WHERE id=? AND owner_id=?",(int(parts[1]),m.from_user.id))
    if cur.rowcount: await m.answer(t(lang,"deleted"))
    else: await m.answer(t(lang,"not_found"))

@router.message(Command("birthdays"))
@router.message(F.text.in_({"🎂 Tug‘ilgan kunlar","🎂 Дни рождения","🎂 Birthdays"}))
async def birthdays(m: Message):
    lang=await ensure(m)
    rows=await DB.fetchall("SELECT id,name,birthday FROM contacts WHERE owner_id=? AND birthday IS NOT NULL ORDER BY substr(birthday,6,5)",(m.from_user.id,))
    if not rows: return await m.answer(t(lang,"no_birthdays"))
    today=date.today()
    out=[]
    for r in rows:
        d=date.fromisoformat(r["birthday"]); nextd=d.replace(year=today.year)
        if nextd < today: nextd=nextd.replace(year=today.year+1)
        out.append((nextd, f'🎂 {esc(r["name"])} — {d.strftime("%d.%m.%Y")} · { (nextd-today).days } kun qoldi'))
    out.sort(key=lambda x:x[0])
    await m.answer("\n".join(x[1] for x in out))

@router.message(Command("schedule"))
@router.message(F.text.in_({"💌 Tabrik rejalashtirish","💌 Запланировать поздравление","💌 Schedule greeting"}))
async def schedule(m: Message, state: FSMContext):
    lang=await ensure(m); await start_greeting(m,state,lang)

@router.message(GreetingFlow.recipient_id)
async def greeting_id(m: Message,state: FSMContext):
    lang=await lang_of(m.from_user.id); v=(m.text or "").strip()
    if not v.isdigit(): return await m.answer("Telegram ID faqat raqam bo‘lishi kerak.")
    await state.update_data(recipient_id=int(v)); await state.set_state(GreetingFlow.recipient_name)
    await m.answer(t(lang,"ask_name"))

@router.message(GreetingFlow.recipient_name)
async def greeting_name(m: Message,state: FSMContext):
    name=(m.text or "").strip()
    if not name or len(name)>100: return await m.answer("Ism 1–100 belgi bo‘lsin.")
    await state.update_data(recipient_name=name); await state.set_state(GreetingFlow.message)
    await m.answer("Tabrik matnini yuboring. HTML teglari qo‘llab-quvvatlanmaydi.")

@router.message(GreetingFlow.message)
async def greeting_message(m: Message,state: FSMContext):
    text=(m.text or "").strip()
    if not text or len(text)>3500: return await m.answer("Matn 1–3500 belgi bo‘lishi kerak.")
    await state.update_data(message=text); await state.set_state(GreetingFlow.send_at)
    await m.answer("Yuborish vaqtini YYYY-MM-DD HH:MM formatida kiriting (Asia/Tashkent).")

@router.message(GreetingFlow.send_at)
async def greeting_time(m: Message,state: FSMContext):
    lang=await lang_of(m.from_user.id)
    try:
        dt=datetime.strptime((m.text or "").strip(),"%Y-%m-%d %H:%M")
        # Treat naive date as Tashkent UTC+5, convert to UTC for durable storage.
        from datetime import timezone
        from datetime import timedelta as td
        dt=dt.replace(tzinfo=timezone(td(hours=5))).astimezone(timezone.utc)
        if dt <= datetime.now(timezone.utc): raise ValueError()
    except ValueError:
        return await m.answer(t(lang,"bad_time"))
    await state.update_data(send_at=dt.isoformat()); await state.set_state(GreetingFlow.media)
    await m.answer(t(lang,"ask_media"))

@router.message(GreetingFlow.media)
async def greeting_media(m: Message,state: FSMContext):
    data=await state.get_data(); media_type=None; media_id=None
    if (m.text or "").strip().lower()!="/skip":
        if m.photo: media_type="photo"; media_id=m.photo[-1].file_id
        elif m.video: media_type="video"; media_id=m.video.file_id
        elif m.animation: media_type="animation"; media_id=m.animation.file_id
        else: return await m.answer("Faqat rasm, video, GIF/animation yoki /skip yuboring.")
    cur=await DB.execute("""INSERT INTO greetings(owner_id,recipient_id,recipient_name,message,send_at,media_type,media_id,created_at)
        VALUES(?,?,?,?,?,?,?,?)""",(m.from_user.id,data["recipient_id"],data["recipient_name"],data["message"],data["send_at"],media_type,media_id,datetime.utcnow().isoformat()))
    await state.clear()
    lang=await lang_of(m.from_user.id)
    await m.answer(t(lang,"scheduled").format(cur.lastrowid), reply_markup=menu(lang))

@router.message(Command("greetings"))
@router.message(F.text.in_({"📨 Tabriklarim","📨 Мои поздравления","📨 My greetings"}))
async def greetings(m: Message):
    lang=await ensure(m)
    rows=await DB.fetchall("SELECT * FROM greetings WHERE owner_id=? ORDER BY send_at DESC LIMIT 30",(m.from_user.id,))
    if not rows: return await m.answer(t(lang,"no_items"))
    kb=[]; lines=["<b>Tabriklar (oxirgi 30 ta)</b>"]
    for r in rows:
        lines.append(f'#{r["id"]} · {esc(r["recipient_name"])} · {r["send_at"][:16]} UTC · {r["status"]} · urinish {r["attempts"]}')
        if r["status"]=="pending":
            kb.append([InlineKeyboardButton(text=f'❌ Bekor qilish #{r["id"]}',callback_data=f'cancelg:{r["id"]}')])
    await m.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb) if kb else None)

@router.callback_query(F.data.startswith("cancelg:"))
async def cancel_greeting(c: CallbackQuery):
    gid=c.data.split(":")[1]
    cur=await DB.execute("UPDATE greetings SET status='cancelled' WHERE id=? AND owner_id=? AND status='pending'",(int(gid),c.from_user.id))
    await c.answer("Bekor qilindi." if cur.rowcount else "Topilmadi.")
    try: await c.message.edit_reply_markup(reply_markup=None)
    except Exception: pass

@router.message(Command("reminders"))
@router.message(F.text.in_({"🔔 Eslatmalar","🔔 Напоминания","🔔 Reminders"}))
async def reminders(m: Message):
    lang=await ensure(m)
    rows=await DB.fetchall("""SELECT r.id,c.name,r.remind_at,r.days_before,r.status FROM reminders r
        JOIN contacts c ON c.id=r.contact_id WHERE r.owner_id=? ORDER BY r.remind_at LIMIT 30""",(m.from_user.id,))
    if not rows: return await m.answer(t(lang,"no_items"))
    await m.answer("\n".join(f'#{r["id"]} · {esc(r["name"])} · {r["days_before"]} kun oldin · {r["remind_at"]} UTC · {r["status"]}' for r in rows))

@router.message(Command("export"))
@router.message(F.text.in_({"📤 CSV eksport","📤 Экспорт CSV","📤 CSV export"}))
async def export_csv(m: Message):
    await ensure(m)
    rows=await DB.fetchall("SELECT name,birthday,telegram_id,notes FROM contacts WHERE owner_id=? ORDER BY name",(m.from_user.id,))
    stream=io.StringIO(); writer=csv.writer(stream)
    writer.writerow(["name","birthday","telegram_id","notes"])
    for r in rows: writer.writerow([r["name"],r["birthday"] or "",r["telegram_id"] or "",r["notes"] or ""])
    file=BufferedInputFile(stream.getvalue().encode("utf-8-sig"),filename="birthday_contacts.csv")
    await m.answer_document(file,caption="Kontaktlar CSV fayli")

@router.message(Command("stats"))
@router.message(F.text.in_({"📊 Statistika","📊 Статистика","📊 Statistics"}))
async def stats(m: Message):
    await ensure(m)
    c=await DB.fetchone("SELECT COUNT(*) n FROM contacts WHERE owner_id=?",(m.from_user.id,))
    g=await DB.fetchone("SELECT COUNT(*) n FROM greetings WHERE owner_id=?",(m.from_user.id,))
    p=await DB.fetchone("SELECT COUNT(*) n FROM greetings WHERE owner_id=? AND status='pending'",(m.from_user.id,))
    s=await DB.fetchone("SELECT COUNT(*) n FROM greetings WHERE owner_id=? AND status='sent'",(m.from_user.id,))
    await m.answer(f"📊 <b>Shaxsiy statistika</b>\n📇 Kontaktlar: {c['n']}\n💌 Tabriklar: {g['n']}\n⏳ Navbatda: {p['n']}\n✅ Yuborilgan: {s['n']}")

@router.message(Command("admin"))
async def admin(m: Message):
    from config import ADMIN_IDS
    if m.from_user.id not in ADMIN_IDS: return await m.answer(t(await lang_of(m.from_user.id),"admin_only"))
    s=await DB.stats()
    await m.answer(f"🛠 <b>Admin statistikasi</b>\n👥 Foydalanuvchilar: {s['users']}\n📇 Kontaktlar: {s['contacts']}\n⏳ Navbatda: {s['pending']}\n✅ Yuborilgan: {s['sent']}\n❌ Xatolik: {s['failed']}\n\nBackup: /backup")

@router.message(Command("backup"))
async def backup(m: Message):
    from config import ADMIN_IDS, BACKUP_DIR, DATABASE_PATH
    import os, shutil
    if m.from_user.id not in ADMIN_IDS: return await m.answer(t(await lang_of(m.from_user.id),"admin_only"))
    os.makedirs(BACKUP_DIR,exist_ok=True)
    path=os.path.join(BACKUP_DIR,f"birthday-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.db")
    # Use SQLite backup API to include a consistent snapshot.
    import sqlite3
    src=sqlite3.connect(DATABASE_PATH); dst=sqlite3.connect(path)
    src.backup(dst); dst.close(); src.close()
    await m.answer_document(BufferedInputFile(open(path,"rb").read(),filename=os.path.basename(path)),caption="Database backup")

@router.message(F.text.in_({"📇 Kontaktlar","📇 Контакты","📇 Contacts"}))
async def contacts_duplicate(m: Message):
    pass
