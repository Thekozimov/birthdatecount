# Birthday Counter Bot PRO MAX

Telegram tug‘ilgan kunlar va rejalashtirilgan tabriklar boti (aiogram 3 + SQLite).

## Imkoniyatlar
- Kontaktlar: ism, tug‘ilgan sana, Telegram ID va izoh.
- Tabrikni sana/vaqtga rejalashtirish; matn va ixtiyoriy foto/video/GIF (Telegram animation).
- Rejalashtirilgan tabriklar ro‘yxati va bekor qilish.
- Tug‘ilgan kunlar ro‘yxati va qolgan kunlarni hisoblash.
- O‘zbek/rus/ingliz tilini tanlash.
- Shaxsiy va admin statistikasi.
- Kontaktlarni CSV eksport qilish.
- Admin uchun SQLite backup.
- Yetkazish holati, xatolar jurnali va cheklangan qayta urinishlar.
- Docker va systemd namunaviy konfiguratsiyalari.

## O‘rnatish (Windows / Termux / Linux)
1. Python 3.11+ o‘rnating.
2. Loyihani oching va terminalni loyiha papkasida ishga tushiring.
3. Virtual muhit yarating:
   - Windows: `python -m venv venv` va `venv\\Scripts\\activate`
   - Linux/Termux: `python -m venv venv` va `source venv/bin/activate`
4. `pip install -r requirements.txt`
5. `.env.example` faylidan `.env` nusxa yarating.
6. `.env` ichida `BOT_TOKEN` ni BotFather tokeniga, `ADMIN_IDS` ni Telegram numeric ID raqamingizga almashtiring.
7. `python main.py`

## Buyruqlar
`/start`, `/help`, `/addcontact`, `/contacts`, `/deletecontact ID`, `/birthdays`,
`/schedule`, `/greetings`, `/reminders`, `/stats`, `/language`, `/export`, `/cancel`.
Admin: `/admin`, `/backup`.

## Tabrik rejalashtirish
Bot so‘ragan ketma-ketlikda qabul qiluvchi Telegram ID, ism, matn, sana-vaqt va ixtiyoriy media yuboring.
Vaqt `YYYY-MM-DD HH:MM` formatida, `Asia/Tashkent` (UTC+5) deb olinadi.
Qabul qiluvchi botga avval `/start` yuborgan bo‘lishi shart. Telegram ID odatda foydalanuvchi tomonidan bot orqali berilgan ID bo‘lishi kerak.

## Muhim cheklovlar
- Telegram bot foydalanuvchiga birinchi bo‘lib yozolmaydi; qabul qiluvchi botni ishga tushirgan bo‘lishi kerak.
- Tabriklarni har yili avtomatik takrorlash bu versiyada kontaktlar uchun to‘liq avtomatik generator sifatida emas; `recurring` maydoni keyingi kengaytirish uchun tayyor.
- Eslatma jadvali bazada tayyor, lekin ushbu paket avtomatik eslatmalarni kontakt kiritilganda yaratmaydi. Eslatmalarni keyingi versiyada to‘liq UI bilan yoqish mumkin.
- Ko‘p tilli menyu va asosiy xabarlar tarjima qilingan; ayrim jarayon xabarlari o‘zbek tilida qolishi mumkin.
- Bu loyiha kod namunasi. Ishga tushirgach test chatda sinang va zaxira nusxasini muntazam oling.

## 24/7 hosting
- VPS yoki doimiy ishlaydigan server kerak.
- Docker: `cd deploy`, `.env` ni loyiha ildiziga qo‘ying, `docker compose up -d --build`.
- systemd namunasi `deploy/birthday-bot.service` ichida. Yo‘llar va Linux foydalanuvchisini serveringizga moslang.
