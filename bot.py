import os
import random
import anthropic
import requests
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

user_histories = {}
user_notes = {}
user_quiz = {}

CITY_MAP = {
    "toshkent": "Tashkent", "toshkend": "Tashkent",
    "samarqand": "Samarkand", "namangan": "Namangan",
    "andijon": "Andijan", "farg'ona": "Fergana", "fargona": "Fergana",
    "buxoro": "Bukhara", "nukus": "Nukus", "qarshi": "Qarshi",
    "termiz": "Termez", "jizzax": "Jizzakh", "navoiy": "Navoi",
    "urganch": "Urgench", "guliston": "Guliston",
}

MENU = ReplyKeyboardMarkup([
    ["🌤 Ob-havo", "💰 Valyuta kursi"],
    ["📝 Eslatmalar", "🗑 Eslatmani o'chirish"],
    ["🌐 Yangiliklar", "🎮 O'yin"],
    ["📊 Slayd yasash", "🤖 AI suhbat"],
    ["ℹ️ Yordam"]
], resize_keyboard=True)

# QUIZ savollari
QUIZ_QUESTIONS = [
    {"q": "O'zbekistonning poytaxti qaysi shahar?", "options": ["Samarqand", "Toshkent", "Buxoro", "Namangan"], "answer": 1},
    {"q": "Dunyo eng baland tog'i qaysi?", "options": ["K2", "Kangchenjunga", "Everest", "Lhotse"], "answer": 2},
    {"q": "1 + 1 = ?", "options": ["1", "2", "3", "4"], "answer": 1},
    {"q": "Quyosh sistemasida nechta sayyora bor?", "options": ["7", "8", "9", "10"], "answer": 1},
    {"q": "Python qaysi turdagi til?", "options": ["Kompilyatsiya", "Interpretatsiya", "Mashina", "Assembly"], "answer": 1},
    {"q": "Internetni kim ixtiro qilgan?", "options": ["Bill Gates", "Steve Jobs", "Tim Berners-Lee", "Elon Musk"], "answer": 2},
    {"q": "O'zbekiston mustaqillikni qachon qo'lga kiritdi?", "options": ["1990", "1991", "1992", "1993"], "answer": 1},
    {"q": "Eng katta okean qaysi?", "options": ["Atlantika", "Hind", "Tinch", "Arktika"], "answer": 2},
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"Salom, {name}! 👋\n\nMen @samik18uz tomonidan yaratilgan AI yordamchiman.\n\nQuyidagi menyudan tanlang:",
        reply_markup=MENU
    )

async def get_weather(city: str) -> str:
    try:
        city_en = CITY_MAP.get(city.lower(), city)
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city_en}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url).json()
        if res.get("cod") != 200:
            return f"❌ '{city}' shahri topilmadi.\n\nQuyidagilarni sinab ko'ring:\nToshkent, Namangan, Samarqand, Andijon, Farg'ona, Buxoro"
        temp = res["main"]["temp"]
        feels = res["main"]["feels_like"]
        humidity = res["main"]["humidity"]
        desc = res["weather"][0]["description"]
        wind = res["wind"]["speed"]
        name = res["name"]
        return (
            f"🌤 *{name}* ob-havosi:\n\n"
            f"🌡 Harorat: *{temp}°C* (his: {feels}°C)\n"
            f"💧 Namlik: *{humidity}%*\n"
            f"💨 Shamol: *{wind} m/s*\n"
            f"📋 Holat: {desc}"
        )
    except:
        return "❌ Ob-havo ma'lumotini olishda xato."

async def get_currency() -> str:
    try:
        url = "https://cbu.uz/oz/arkhiv-kursov-valyut/json/"
        res = requests.get(url).json()
        wanted = ["USD", "EUR", "RUB", "GBP", "CNY", "KZT"]
        lines = ["💰 *O'zbekiston Markaziy banki kurslari:*\n"]
        for item in res:
            if item["Ccy"] in wanted:
                rate = float(item["Rate"])
                lines.append(f"*{item['Ccy']}* — {rate:,.2f} so'm")
        lines.append(f"\n📅 Sana: {res[0]['Date']}")
        return "\n".join(lines)
    except:
        return "❌ Valyuta kursini olishda xato."

async def search_web(query: str) -> str:
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": 3,
            "search_depth": "basic"
        }
        res = requests.post(url, json=payload).json()
        results = res.get("results", [])
        if not results:
            return "❌ Natija topilmadi."
        lines = [f"🌐 *'{query}' bo'yicha natijalar:*\n"]
        for i, r in enumerate(results[:3], 1):
            lines.append(f"{i}. *{r['title']}*\n{r['content'][:200]}...\n")
        return "\n".join(lines)
    except:
        return "❌ Qidirishda xato yuz berdi."

async def make_slides(topic: str) -> str:
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system="Siz prezentatsiya mutaxassisisiz. Foydalanuvchi so'ragan mavzu bo'yicha 5 ta slayd tayyorlang. Har bir slayd: sarlavha va 3-4 ta asosiy nuqta. O'zbek tilida yozing. Format:\n🎯 Slayd 1: [Sarlavha]\n• Nuqta 1\n• Nuqta 2\n• Nuqta 3",
            messages=[{"role": "user", "content": f"Mavzu: {topic}"}]
        )
        return f"📊 *{topic}* bo'yicha slaydlar:\n\n" + response.content[0].text
    except:
        return "❌ Slayd yaratishda xato."

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    q = random.choice(QUIZ_QUESTIONS)
    user_quiz[user_id] = {"answer": q["answer"], "score": user_quiz.get(user_id, {}).get("score", 0)}
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(q["options"][0], callback_data="quiz_0"),
         InlineKeyboardButton(q["options"][1], callback_data="quiz_1")],
        [InlineKeyboardButton(q["options"][2], callback_data="quiz_2"),
         InlineKeyboardButton(q["options"][3], callback_data="quiz_3")],
    ])
    score = user_quiz[user_id]["score"]
    await update.message.reply_text(
        f"🎮 *Viktorina!*\n\n❓ {q['q']}\n\n🏆 Ball: {score}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id not in user_quiz:
        await query.edit_message_text("❌ O'yin topilmadi. /start bosing.")
        return
    
    chosen = int(query.data.split("_")[1])
    correct = user_quiz[user_id]["answer"]
    
    if chosen == correct:
        user_quiz[user_id]["score"] = user_quiz[user_id].get("score", 0) + 1
        result = f"✅ *To'g'ri!* +1 ball\n🏆 Jami ball: {user_quiz[user_id]['score']}"
    else:
        result = f"❌ *Noto'g'ri!*\n🏆 Jami ball: {user_quiz[user_id].get('score', 0)}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Keyingi savol", callback_data="quiz_next")]
    ])
    await query.edit_message_text(result, parse_mode="Markdown", reply_markup=keyboard)

async def quiz_next_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    q = random.choice(QUIZ_QUESTIONS)
    user_quiz[user_id]["answer"] = q["answer"]
    score = user_quiz[user_id].get("score", 0)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(q["options"][0], callback_data="quiz_0"),
         InlineKeyboardButton(q["options"][1], callback_data="quiz_1")],
        [InlineKeyboardButton(q["options"][2], callback_data="quiz_2"),
         InlineKeyboardButton(q["options"][3], callback_data="quiz_3")],
    ])
    await query.edit_message_text(
        f"🎮 *Viktorina!*\n\n❓ {q['q']}\n\n🏆 Ball: {score}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text == "🌤 Ob-havo":
        await update.message.reply_text("Qaysi shahar?\n\nMasalan: *Toshkent, Namangan, Samarqand*", parse_mode="Markdown")
        context.user_data["mode"] = "weather"
        return

    if text == "💰 Valyuta kursi":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        result = await get_currency()
        await update.message.reply_text(result, parse_mode="Markdown", reply_markup=MENU)
        return

    if text == "🌐 Yangiliklar":
        await update.message.reply_text("Nima haqida qidirmoqchisiz?\n\nMasalan: *AI yangiliklari, Uzbekistan news*", parse_mode="Markdown")
        context.user_data["mode"] = "search"
        return

    if text == "🎮 O'yin":
        await start_quiz(update, context)
        return

    if text == "📊 Slayd yasash":
        await update.message.reply_text("Qaysi mavzuda slayd kerak?\n\nMasalan: *Sun'iy intellekt, Iqlim o'zgarishi*", parse_mode="Markdown")
        context.user_data["mode"] = "slides"
        return

    if text == "📝 Eslatmalar":
        notes = user_notes.get(user_id, [])
        if not notes:
            await update.message.reply_text("📝 Eslatmalaringiz yo'q.\n\nYaratish: *eslatma: matn*", parse_mode="Markdown")
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
            await update.message.reply_text(f"*Qaysi raqamni o'chirish?*\n\n{note_list}\n\nRaqamni yozing:", parse_mode="Markdown")
            context.user_data["mode"] = "delete_note"
        return

    if text == "🤖 AI suhbat":
        await update.message.reply_text("Savolingizni yozing! 🤖")
        context.user_data["mode"] = "ai"
        return

    if text == "ℹ️ Yordam":
        await update.message.reply_text(
            "ℹ️ *Yordam:*\n\n"
            "🌤 *Ob-havo* — shahar ob-havosi\n"
            "💰 *Valyuta* — Markaziy bank kurslari\n"
            "🌐 *Yangiliklar* — internet qidirish\n"
            "🎮 *O'yin* — viktorina o'yni\n"
            "📊 *Slayd* — prezentatsiya yaratish\n"
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
            await update.message.reply_text(f"✅ Saqlandi: *{note}*", parse_mode="Markdown")
        return

    mode = context.user_data.get("mode", "ai")

    if mode == "weather":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        result = await get_weather(text)
        await update.message.reply_text(result, parse_mode="Markdown", reply_markup=MENU)
        context.user_data["mode"] = "ai"
        return

    if mode == "search":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        result = await search_web(text)
        await update.message.reply_text(result, parse_mode="Markdown", reply_markup=MENU)
        context.user_data["mode"] = "ai"
        return

    if mode == "slides":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        result = await make_slides(text)
        await update.message.reply_text(result, parse_mode="Markdown", reply_markup=MENU)
        context.user_data["mode"] = "ai"
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
            system="Siz @samik18uz tomonidan yaratilgan AI yordamchisiz. Claude yoki Anthropic haqida gapirmaysiz. Kim yaratgani so'ralsa '@samik18uz yaratgan' deng. Foydalanuvchi qaysi tilda yozsa shu tilda javob bering. Qisqa va aniq javob bering.",
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
    app.add_handler(CallbackQueryHandler(quiz_next_callback, pattern="^quiz_next$"))
    app.add_handler(CallbackQueryHandler(quiz_callback, pattern="^quiz_[0-9]$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot ishga tushdi! ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
