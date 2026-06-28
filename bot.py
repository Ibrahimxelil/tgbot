"""
AutoCheck-in Telegram Botu
Uçuş check-in işlemini otomatik yapar.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database
from checkin import CheckinService
import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Konuşma adımları
AIRLINE, PNR, LASTNAME, DATE, CONFIRM = range(5)

db = Database()
scheduler = AsyncIOScheduler()
checkin_service = CheckinService()

# --- Yardımcı ---

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✈️ Uçuş Ekle", callback_data="add_flight")],
        [InlineKeyboardButton("📋 Uçuşlarım", callback_data="my_flights")],
        [InlineKeyboardButton("ℹ️ Nasıl Çalışır?", callback_data="how_it_works")],
    ])

def airline_keyboard():
    airlines = config.SUPPORTED_AIRLINES
    buttons = [[InlineKeyboardButton(a, callback_data=f"airline_{a}")] for a in airlines]
    buttons.append([InlineKeyboardButton("❌ İptal", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)

# --- Komutlar ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "", user.first_name or "")
    await update.message.reply_text(
        f"👋 Merhaba *{user.first_name}*!\n\n"
        "Ben *AutoCheck-in* botuyum.\n"
        "Uçuşunuzu ekleyin, check-in zamanı geldiğinde otomatik olarak yapayım ve boarding pass'inizi size göndereyim. ✅\n\n"
        "Ne yapmak istersiniz?",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Yardım*\n\n"
        "*/start* — Ana menü\n"
        "*/add* — Uçuş ekle\n"
        "*/flights* — Uçuşlarımı görüntüle\n"
        "*/cancel* — İşlemi iptal et\n\n"
        "Sorun mu yaşıyorsunuz? @destek kullanıcısına yazın.",
        parse_mode="Markdown"
    )

# --- Uçuş ekleme akışı ---

async def add_flight_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "✈️ *Havayolunu seçin:*",
            parse_mode="Markdown",
            reply_markup=airline_keyboard()
        )
    else:
        await update.message.reply_text(
            "✈️ *Havayolunu seçin:*",
            parse_mode="Markdown",
            reply_markup=airline_keyboard()
        )
    return AIRLINE

async def airline_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    airline = query.data.replace("airline_", "")
    context.user_data["airline"] = airline
    await query.edit_message_text(
        f"✅ Havayolu: *{airline}*\n\n"
        "📝 *Rezervasyon kodunuzu (PNR) girin:*\n"
        "_Örnek: ABC123_",
        parse_mode="Markdown"
    )
    return PNR

async def pnr_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pnr = update.message.text.strip().upper()
    if len(pnr) < 5 or len(pnr) > 10:
        await update.message.reply_text("⚠️ Geçersiz PNR. Lütfen tekrar girin (5-10 karakter):")
        return PNR
    context.user_data["pnr"] = pnr
    await update.message.reply_text(
        f"✅ PNR: *{pnr}*\n\n"
        "👤 *Soyadınızı girin* (bilet üzerindeki gibi, büyük harfle):\n"
        "_Örnek: YILMAZ_",
        parse_mode="Markdown"
    )
    return LASTNAME

async def lastname_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lastname = update.message.text.strip().upper()
    context.user_data["lastname"] = lastname
    await update.message.reply_text(
        f"✅ Soyad: *{lastname}*\n\n"
        "📅 *Uçuş tarihini girin* (GG.AA.YYYY formatında):\n"
        "_Örnek: 29.06.2026_",
        parse_mode="Markdown"
    )
    return DATE

async def date_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text.strip()
    try:
        flight_date = datetime.strptime(date_text, "%d.%m.%Y")
        if flight_date.date() < datetime.now().date():
            await update.message.reply_text("⚠️ Geçmiş tarih girilemez. Lütfen tekrar deneyin:")
            return DATE
    except ValueError:
        await update.message.reply_text("⚠️ Tarih formatı hatalı. GG.AA.YYYY olmalı (ör: 29.06.2026):")
        return DATE

    context.user_data["flight_date"] = flight_date

    airline = context.user_data["airline"]
    pnr = context.user_data["pnr"]
    lastname = context.user_data["lastname"]

    confirm_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Onayla", callback_data="confirm_add")],
        [InlineKeyboardButton("❌ İptal", callback_data="cancel")],
    ])

    await update.message.reply_text(
        "📋 *Uçuş Bilgileri*\n\n"
        f"✈️ Havayolu: *{airline}*\n"
        f"🎫 PNR: *{pnr}*\n"
        f"👤 Soyad: *{lastname}*\n"
        f"📅 Tarih: *{flight_date.strftime('%d.%m.%Y')}*\n\n"
        "Check-in uçuştan 24 saat önce otomatik yapılacak.\n"
        "Onaylıyor musunuz?",
        parse_mode="Markdown",
        reply_markup=confirm_keyboard
    )
    return CONFIRM

async def confirm_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = context.user_data

    flight_id = db.add_flight(
        user_id=user_id,
        airline=data["airline"],
        pnr=data["pnr"],
        lastname=data["lastname"],
        flight_date=data["flight_date"]
    )

    # Zamanlayıcıyı ayarla
    checkin_time = data["flight_date"] - timedelta(hours=24)
    if checkin_time > datetime.now():
        scheduler.add_job(
            do_checkin,
            "date",
            run_date=checkin_time,
            args=[user_id, flight_id, query.message.chat_id],
            id=f"checkin_{flight_id}"
        )
        time_str = checkin_time.strftime("%d.%m.%Y %H:%M")
        schedule_msg = f"⏰ Check-in zamanı: *{time_str}*"
    else:
        # 24 saatten az kalmışsa hemen dene
        asyncio.create_task(do_checkin(user_id, flight_id, query.message.chat_id))
        schedule_msg = "⚡ Check-in 24 saatten az kaldı, hemen deneniyor..."

    await query.edit_message_text(
        "🎉 *Uçuş eklendi!*\n\n"
        f"{schedule_msg}\n\n"
        "Check-in tamamlandığında sizi bilgilendireceğim. ✅",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Uçuşlarımı Gör", callback_data="my_flights")],
            [InlineKeyboardButton("✈️ Başka Uçuş Ekle", callback_data="add_flight")],
        ])
    )
    context.user_data.clear()
    return ConversationHandler.END

# --- Uçuşları listele ---

async def my_flights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    user_id = update.effective_user.id
    flights = db.get_user_flights(user_id)

    if not flights:
        text = "📋 *Uçuşlarınız*\n\nHenüz kayıtlı uçuşunuz yok."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✈️ Uçuş Ekle", callback_data="add_flight")]])
    else:
        text = "📋 *Uçuşlarınız*\n\n"
        buttons = []
        for f in flights:
            status_emoji = {"pending": "⏳", "done": "✅", "failed": "❌"}.get(f["status"], "⏳")
            text += (
                f"{status_emoji} *{f['airline']}* — {f['pnr']}\n"
                f"   📅 {f['flight_date']} | 👤 {f['lastname']}\n"
                f"   Durum: {f['status_text']}\n\n"
            )
            if f["status"] == "done" and f.get("boarding_pass"):
                buttons.append([InlineKeyboardButton(
                    f"📄 Boarding Pass ({f['pnr']})",
                    callback_data=f"bp_{f['id']}"
                )])
        kb = InlineKeyboardMarkup(buttons + [[InlineKeyboardButton("✈️ Uçuş Ekle", callback_data="add_flight")]])

    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

# --- Check-in işlemi ---

async def do_checkin(user_id: int, flight_id: int, chat_id: int):
    """Gerçek check-in işlemi burada yapılır."""
    flight = db.get_flight(flight_id)
    if not flight:
        return

    logger.info(f"Check-in başladı: {flight['airline']} {flight['pnr']}")
    db.update_flight_status(flight_id, "in_progress")

    # Kullanıcıya bildir
    from bot_instance import app
    await app.bot.send_message(
        chat_id=chat_id,
        text=f"⚙️ *Check-in başladı!*\n\n"
             f"✈️ {flight['airline']} — {flight['pnr']}\n"
             f"Lütfen bekleyin...",
        parse_mode="Markdown"
    )

    # Check-in servisini çalıştır
    result = await checkin_service.do_checkin(
        airline=flight["airline"],
        pnr=flight["pnr"],
        lastname=flight["lastname"]
    )

    if result["success"]:
        db.update_flight_status(flight_id, "done", boarding_pass=result.get("boarding_pass_url"))
        msg = (
            f"✅ *Check-in tamamlandı!*\n\n"
            f"✈️ {flight['airline']} — {flight['pnr']}\n"
            f"💺 Koltuk: *{result.get('seat', 'Belirtilmedi')}*\n\n"
        )
        if result.get("boarding_pass_url"):
            msg += f"📄 [Boarding Pass'i İndir]({result['boarding_pass_url']})"
    else:
        db.update_flight_status(flight_id, "failed")
        msg = (
            f"❌ *Check-in başarısız!*\n\n"
            f"✈️ {flight['airline']} — {flight['pnr']}\n"
            f"Sebep: {result.get('error', 'Bilinmeyen hata')}\n\n"
            "Lütfen manuel olarak check-in yapmayı deneyin."
        )

    await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

# --- Callback handler ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "my_flights":
        await my_flights(update, context)
    elif query.data == "how_it_works":
        await query.edit_message_text(
            "ℹ️ *Nasıl Çalışır?*\n\n"
            "1️⃣ Uçuş bilgilerinizi girin (havayolu, PNR, soyad, tarih)\n"
            "2️⃣ Bot uçuşunuzu kaydeder\n"
            "3️⃣ Uçuştan tam *24 saat önce* otomatik check-in yapılır\n"
            "4️⃣ Boarding pass size anında gönderilir ✅\n\n"
            "🔒 Bilgileriniz güvenli şekilde saklanır ve sadece check-in için kullanılır.\n\n"
            f"📌 Desteklenen havayolları: {', '.join(config.SUPPORTED_AIRLINES)}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Geri", callback_data="back_main")
            ]])
        )
    elif query.data == "back_main":
        await query.edit_message_text(
            "Ne yapmak istersiniz?",
            reply_markup=main_menu_keyboard()
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ İşlem iptal edildi.", reply_markup=main_menu_keyboard())
    else:
        await update.message.reply_text("❌ İşlem iptal edildi.", reply_markup=main_menu_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# --- Ana fonksiyon ---

def main():
    global app
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Uçuş ekleme konuşması
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_flight_start),
            CallbackQueryHandler(add_flight_start, pattern="^add_flight$"),
        ],
        states={
            AIRLINE: [CallbackQueryHandler(airline_selected, pattern="^airline_")],
            PNR: [MessageHandler(filters.TEXT & ~filters.COMMAND, pnr_received)],
            LASTNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, lastname_received)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_received)],
            CONFIRM: [CallbackQueryHandler(confirm_add, pattern="^confirm_add$")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("flights", my_flights))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    # Zamanlayıcıyı başlat
    scheduler.start()

    # Bekleyen check-in'leri yükle (bot yeniden başlatılırsa)
    pending = db.get_pending_flights()
    for flight in pending:
        checkin_time = flight["checkin_time"]
        if checkin_time > datetime.now():
            scheduler.add_job(
                do_checkin,
                "date",
                run_date=checkin_time,
                args=[flight["user_id"], flight["id"], flight["chat_id"]],
                id=f"checkin_{flight['id']}",
                replace_existing=True
            )

    logger.info("Bot başlatıldı ✅")
    app.run_polling(drop_pending_updates=True)

# Bot instance'ı diğer modüller için
import bot_instance
app = None

if __name__ == "__main__":
    main()
