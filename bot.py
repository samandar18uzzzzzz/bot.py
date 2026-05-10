import os
import anthropic
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Kalitlar Railway environment variables dan o'qiladi
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

user_histories = {}
user_notes = {}

MENU = ReplyKeyboardMarkup([
    ["🌤 Ob-havo", "💰 Valyuta kursi"],
    ["📝 Eslatmalar", "🗑 Eslatmani o'chirish"],
    ["🤖 AI suhbat", "ℹ️ Yordam"]
], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"Salom, {name}! 👋\n\nMen @samik18uz tomonidan yaratilgan AI yordamchiman.\n\nQuyidagi menyudan tanlang:",
        reply_markup=MENU
    )

async def get_weather(city: str) -> str:
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=uz"
        res = requests.get(url).json()
        if res.get("cod") != 200:
            return f"❌ '{city}' shahri topilmadi."
        temp = res["main"]["temp"]
        feels = res["main"]["feels_like"]
        humidity = res["main"]["humidity"]
        desc = res["weather"][0]["description"]
        wind = res["wind"]["speed"]
        return (
            f"🌤 *{city.title()}* ob-havosi:\n\n"
            f"🌡 Harorat: *{temp}°C* (his: {feels}°C)\n"
            f"💧 Namlik: *{humidity}%*\n"
            f"💨 Shamol: *{wind} m/s*\n"
            f"📋 Holat: {desc}"
        )
    except:
        return "❌ Ob-havo ma'lumotini olishda xato."

async def get_currency(amount: float, from_cur: str, to_cur: str) -> str:
    try:
        url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/pair/{from_cur}/{to_cur}/{amount}"
        res = requests.get(url).json()
        if res.get("result") != "success":
            return "❌ Valyuta topilmadi. Masalan: 100 USD UZS"
        rate = res["conversion_rate"]
        result = res["conversion_result"]
        return (
            f"💰 *Valyuta kursi:*\n\n"
            f"{amount} {from_cur.upper()} = *{result:,.2f} {to_cur.upper()}*\n"
            f"1 {from_cur.upper()} = {rate:,.4f} {to_cur.upper()}"
        )
    except:
        return "❌ Valyuta kursini olishda xato."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text == "🌤 Ob-havo":
        await update.message.reply_text("Qaysi shahar ob-havosin bilmoqchisiz?\nMasalan: *Toshkent*", parse_mode="Markdown")
        context.user_data["mode"] = "weather"
        return

    if text == "💰 Valyuta kursi":
        await update.message.reply_text("Quyidagi formatda yozing:\n*100 USD UZS*\n\nMasalan: 50 EUR USD", parse_mode="Markdown")
        context.user_data["mode"] = "currency"
        return

    if text == "📝 Eslatmalar":
        notes = user_notes.get(user_id, [])
        if not notes:
            await update.message.reply_text("📝 Eslatmalaringiz yo'q.\n\nYaratish uchun yozing:\n*eslatma: matn*", parse_mode="Markdown")
        else:
            note_list = "\n".join([f"{i+1}. {n}" for i, n in enumerate(notes)])
            await update.message.reply_text(f"📝 *Eslatmalaringiz:*\n\n{note_list}", parse_mode="Markdown")
        return

    if text == "🗑 Eslatmani o'chirish":
        notes = user_notes.get(user_id, [])
        if not notes:
            await update.message.reply_text("Eslatmalaringiz yo'q.")
        else:
            note_list = "\n".join([f"{i+1}. {n}" for i, n in enumerate(notes)])
            await update.message.reply_text(f"📝 *Qaysi raqamni o'chirish?*\n\n{note_list}\n\nRaqamni yozing:", parse_mode="Markdown")
            context.user_data["mode"] = "delete_note"
        return

    if text == "🤖 AI suhbat":
        await update.message.reply_text("Savolingizni yozing, javob beraman! 🤖")
        context.user_data["mode"] = "ai"
        return

    if text == "ℹ️ Yordam":
        await update.message.reply_text(
            "ℹ️ *Yordam:*\n\n"
            "🌤 *Ob-havo* — shahar ob-havosi\n"
            "💰 *Valyuta* — kurs hisoblash\n"
            "📝 *Eslatmalar* — eslatma saqlash\n"
            "🤖 *AI suhbat* — istalgan savol\n\n"
            "Eslatma qo'shish: *eslatma: matn*",
            parse_mode="Markdown",
            reply_markup=MENU
        )
        return

    if text.lower().startswith("eslatma:"):
        note = text[8:].strip()
        if note:
            if user_id not in user_notes:
                user_notes[user_id] = []
            user_notes[user_id].append(note)
            await update.message.reply_text(f"✅ Eslatma saqlandi: *{note}*", parse_mode="Markdown")
        return

    mode = context.user_data.get("mode", "ai")

    if mode == "weather":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        result = await get_weather(text)
        await update.message.reply_text(result, parse_mode="Markdown", reply_markup=MENU)
        context.user_data["mode"] = "ai"
        return

    if mode == "currency":
        parts = text.upper().split()
        if len(parts) == 3:
            try:
                amount = float(parts[0])
                result = await get_currency(amount, parts[1], parts[2])
                await update.message.reply_text(result, parse_mode="Markdown", reply_markup=MENU)
                context.user_data["mode"] = "ai"
                return
            except:
                await update.message.reply_text("❌ Format noto'g'ri. Masalan: *100 USD UZS*", parse_mode="Markdown")
                return
        else:
            await update.message.reply_text("❌ Format noto'g'ri. Masalan: *100 USD UZS*", parse_mode="Markdown")
            return

    if mode == "delete_note":
        try:
            idx = int(text) - 1
            notes = user_notes.get(user_id, [])
            if 0 <= idx < len(notes):
                deleted = notes.pop(idx)
                await update.message.reply_text(f"🗑 O'chirildi: *{deleted}*", parse_mode="Markdown", reply_markup=MENU)
            else:
                await update.message.reply_text("❌ Noto'g'ri raqam.")
        except:
            await update.message.reply_text("❌ Raqam kiriting.")
        context.user_data["mode"] = "ai"
        return

    # AI suhbat
    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": text})
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system="Siz @samik18uz tomonidan yaratilgan AI yordamchisiz. Siz Claude yoki Anthropic haqida hech qachon gapirmaysiz. Agar kim ekaningiz yoki kim yaratgani haqida so'rashsa, faqat '@samik18uz yaratgan AI yordamchiman' deb ayting. Foydalanuvchi qaysi tilda yozsa, shu tilda javob bering. Qisqa va aniq javob bering.",
            messages=user_histories[user_id]
        )
        reply = response.content[0].text
        user_histories[user_id].append({"role": "assistant", "content": reply})

        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]

        await update.message.reply_text(reply, reply_markup=MENU)

    except Exception as e:
        await update.message.reply_text("❌ Xato yuz berdi. Qayta urinib ko'ring.")
        print(f"Xato: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot ishga tushdi! ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
