import os
import random
import io
import json
import anthropic
import requests
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY")

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

QUIZ_QUESTIONS = [
    {"q": "O'zbekistonning poytaxti?", "options": ["Samarqand", "Toshkent", "Buxoro", "Namangan"], "answer": 1},
    {"q": "Dunyo eng baland tog'i?", "options": ["K2", "Kangchenjunga", "Everest", "Lhotse"], "answer": 2},
    {"q": "Quyosh sistemasida nechta sayyora?", "options": ["7", "8", "9", "10"], "answer": 1},
    {"q": "Internetni kim ixtiro qilgan?", "options": ["Bill Gates", "Steve Jobs", "Tim Berners-Lee", "Elon Musk"], "answer": 2},
    {"q": "O'zbekiston mustaqillikni qachon oldi?", "options": ["1990", "1991", "1992", "1993"], "answer": 1},
    {"q": "Eng katta okean?", "options": ["Atlantika", "Hind", "Tinch", "Arktika"], "answer": 2},
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"Salom, {name}! 👋\n\nMen @Samik_1806 tomonidan yaratilgan AI yordamchiman.\n\nQuyidagi menyudan tanlang:",
        reply_markup=MENU
    )

async def get_weather(city: str) -> str:
    try:
        city_en = CITY_MAP.get(city.lower(), city)
        res = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={city_en}&appid={WEATHER_API_KEY}&units=metric").json()
        if res.get("cod") != 200:
            return f"❌ '{city}' topilmadi.\n\nSinab ko'ring: Toshkent, Namangan, Samarqand"
        return (
            f"🌤 *{res['name']}* ob-havosi:\n\n"
            f"🌡 Harorat: *{res['main']['temp']}°C* (his: {res['main']['feels_like']}°C)\n"
            f"💧 Namlik: *{res['main']['humidity']}%*\n"
            f"💨 Shamol: *{res['wind']['speed']} m/s*\n"
            f"📋 Holat: {res['weather'][0]['description']}"
        )
    except:
        return "❌ Ob-havo ma'lumotini olishda xato."

async def get_currency() -> str:
    try:
        res = requests.get("https://cbu.uz/oz/arkhiv-kursov-valyut/json/").json()
        wanted = ["USD", "EUR", "RUB", "GBP", "CNY", "KZT"]
        lines = ["💰 *Markaziy bank kurslari:*\n"]
        for item in res:
            if item["Ccy"] in wanted:
                lines.append(f"*{item['Ccy']}* — {float(item['Rate']):,.2f} so'm")
        lines.append(f"\n📅 {res[0]['Date']}")
        return "\n".join(lines)
    except:
        return "❌ Valyuta kursini olishda xato."

async def search_web(query: str) -> str:
    try:
        res = requests.post("https://api.tavily.com/search", json={
            "api_key": TAVILY_API_KEY, "query": query, "max_results": 3
        }).json()
        results = res.get("results", [])
        if not results:
            return "❌ Natija topilmadi."
        lines = [f"🌐 *'{query}' natijalari:*\n"]
        for i, r in enumerate(results[:3], 1):
            lines.append(f"{i}. *{r['title']}*\n{r['content'][:200]}...\n")
        return "\n".join(lines)
    except:
        return "❌ Qidirishda xato."

def get_unsplash_image(query: str) -> bytes | None:
    try:
        res = requests.get(
            f"https://api.unsplash.com/search/photos?query={query}&per_page=1&orientation=landscape",
            headers={"Authorization": f"Client-ID {UNSPLASH_API_KEY}"}
        ).json()
        photos = res.get("results", [])
        if not photos:
            return None
        img_url = photos[0]["urls"]["regular"]
        img_data = requests.get(img_url).content
        return img_data
    except:
        return None

def create_pptx(topic: str, slides_data: list) -> io.BytesIO:
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    BG_COLOR = RGBColor(12, 12, 22)
    ACCENT = RGBColor(80, 180, 255)
    WHITE = RGBColor(255, 255, 255)
    GRAY = RGBColor(160, 160, 180)
    OVERLAY = RGBColor(12, 12, 22)

    for i, slide_data in enumerate(slides_data):
        slide = prs.slides.add_slide(prs.slide_layouts[6])

        # Fon
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = BG_COLOR

        # Unsplash rasm olish
        search_query = slide_data.get("image_query", topic)
        img_bytes = get_unsplash_image(search_query)

        if img_bytes:
            img_stream = io.BytesIO(img_bytes)
            # Rasmni to'liq fonga qo'yish
            slide.shapes.add_picture(img_stream, Inches(0), Inches(0), Inches(13.33), Inches(7.5))
            # Qoramtir shaffof qatlam
            overlay = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.33), Inches(7.5))
            overlay.fill.solid()
            overlay.fill.fore_color.rgb = RGBColor(10, 10, 20)
            overlay.line.fill.background()
            from lxml import etree
            sp = overlay.element
            spPr = sp.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill")
            if spPr is not None:
                alpha = etree.SubElement(spPr.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr"), "{http://schemas.openxmlformats.org/drawingml/2006/main}alpha")
                alpha.set("val", "75000")

        # Chiziq
        line = slide.shapes.add_shape(1, Inches(0), Inches(1.7), Inches(7.3), Pt(1.5))
        line.fill.solid()
        line.fill.fore_color.rgb = ACCENT
        line.line.fill.background()

        # Slayd raqami
        num_box = slide.shapes.add_textbox(Inches(0.3), Inches(0.2), Inches(1), Inches(0.5))
        tf = num_box.text_frame
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = f"{i+1:02d}"
        r.font.size = Pt(13)
        r.font.color.rgb = ACCENT
        r.font.bold = True

        # Sarlavha
        title_box = slide.shapes.add_textbox(Inches(0.3), Inches(0.3), Inches(6.8), Inches(1.3))
        tf2 = title_box.text_frame
        tf2.word_wrap = True
        p2 = tf2.paragraphs[0]
        r2 = p2.add_run()
        r2.text = slide_data["title"]
        r2.font.size = Pt(30) if i == 0 else Pt(24)
        r2.font.bold = True
        r2.font.color.rgb = WHITE

        # Kontent nuqtalari
        content_box = slide.shapes.add_textbox(Inches(0.3), Inches(1.9), Inches(6.8), Inches(5.2))
        tf3 = content_box.text_frame
        tf3.word_wrap = True

        for j, point in enumerate(slide_data["points"]):
            p3 = tf3.paragraphs[0] if j == 0 else tf3.add_paragraph()
            p3.space_before = Pt(10)
            r3 = p3.add_run()
            r3.text = f"▸  {point}"
            r3.font.size = Pt(16)
            r3.font.color.rgb = WHITE

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf

async def make_pptx(topic: str) -> tuple:
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system="""Siz prezentatsiya mutaxassisisiz. 6 ta slayd uchun JSON tayyorlang.
Faqat JSON qaytaring. Format:
[
  {"title": "Sarlavha", "points": ["Nuqta 1", "Nuqta 2", "Nuqta 3"], "image_query": "inglizcha rasm qidirish so'zi"},
  ...
]
O'zbek tilida yozing. image_query inglizcha bo'lsin (Unsplash uchun).""",
            messages=[{"role": "user", "content": f"Mavzu: {topic}"}]
        )
        text = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        slides_data = json.loads(text)
        pptx_file = create_pptx(topic, slides_data)
        return pptx_file, None
    except Exception as e:
        return None, f"❌ Slayd yaratishda xato: {e}"

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    q = random.choice(QUIZ_QUESTIONS)
    if user_id not in user_quiz:
        user_quiz[user_id] = {"score": 0}
    user_quiz[user_id]["answer"] = q["answer"]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(q["options"][0], callback_data="quiz_0"),
         InlineKeyboardButton(q["options"][1], callback_data="quiz_1")],
        [InlineKeyboardButton(q["options"][2], callback_data="quiz_2"),
         InlineKeyboardButton(q["options"][3], callback_data="quiz_3")],
    ])
    await update.message.reply_text(
        f"🎮 *Viktorina!*\n\n❓ {q['q']}\n\n🏆 Ball: {user_quiz[user_id]['score']}",
        parse_mode="Markdown", reply_markup=keyboard
    )

async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in user_quiz:
        await query.edit_message_text("❌ /start bosing.")
        return
    chosen = int(query.data.split("_")[1])
    if chosen == user_quiz[user_id]["answer"]:
        user_quiz[user_id]["score"] += 1
        result = f"✅ *To'g'ri!* +1 ball\n🏆 Jami: {user_quiz[user_id]['score']}"
    else:
        result = f"❌ *Noto'g'ri!*\n🏆 Jami: {user_quiz[user_id]['score']}"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Keyingi", callback_data="quiz_next")]])
    await query.edit_message_text(result, parse_mode="Markdown", reply_markup=keyboard)

async def quiz_next_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    q = random.choice(QUIZ_QUESTIONS)
    if user_id not in user_quiz:
        user_quiz[user_id] = {"score": 0}
    user_quiz[user_id]["answer"] = q["answer"]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(q["options"][0], callback_data="quiz_0"),
         InlineKeyboardButton(q["options"][1], callback_data="quiz_1")],
        [InlineKeyboardButton(q["options"][2], callback_data="quiz_2"),
         InlineKeyboardButton(q["options"][3], callback_data="quiz_3")],
    ])
    await query.edit_message_text(
        f"🎮 *Viktorina!*\n\n❓ {q['q']}\n\n🏆 Ball: {user_quiz[user_id]['score']}",
        parse_mode="Markdown", reply_markup=keyboard
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text == "🌤 Ob-havo":
        await update.message.reply_text("Qaysi shahar?\n\nMasalan: *Toshkent, Namangan*", parse_mode="Markdown")
        context.user_data["mode"] = "weather"
        return
    if text == "💰 Valyuta kursi":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await update.message.reply_text(await get_currency(), parse_mode="Markdown", reply_markup=MENU)
        return
    if text == "🌐 Yangiliklar":
        await update.message.reply_text("Nima haqida qidirmoqchisiz?")
        context.user_data["mode"] = "search"
        return
    if text == "🎮 O'yin":
        await start_quiz(update, context)
        return
    if text == "📊 Slayd yasash":
        await update.message.reply_text("Qaysi mavzuda slayd?\n\nMasalan: *Sun'iy intellekt, Iqlim o'zgarishi*", parse_mode="Markdown")
        context.user_data["mode"] = "slides"
        return
    if text == "📝 Eslatmalar":
        notes = user_notes.get(user_id, [])
        if not notes:
            await update.message.reply_text("📝 Eslatma yo'q.\n\nQo'shish: *eslatma: matn*", parse_mode="Markdown")
        else:
            await update.message.reply_text("📝 *Eslatmalar:*\n\n" + "\n".join([f"{i+1}. {n}" for i, n in enumerate(notes)]), parse_mode="Markdown")
        return
    if text == "🗑 Eslatmani o'chirish":
        notes = user_notes.get(user_id, [])
        if not notes:
            await update.message.reply_text("Eslatma yo'q.")
        else:
            await update.message.reply_text("*Qaysi raqam?*\n\n" + "\n".join([f"{i+1}. {n}" for i, n in enumerate(notes)]), parse_mode="Markdown")
            context.user_data["mode"] = "delete_note"
        return
    if text == "🤖 AI suhbat":
        await update.message.reply_text("Savolingizni yozing! 🤖")
        context.user_data["mode"] = "ai"
        return
    if text == "ℹ️ Yordam":
        await update.message.reply_text(
            "ℹ️ *Yordam:*\n\n🌤 Ob-havo • 💰 Valyuta\n🌐 Yangiliklar • 🎮 Viktorina\n📊 PPTX slayd (rasimli!) • 📝 Eslatmalar\n🤖 AI suhbat\n\nYaratuvchi: @Samik_1806\nEslatma: *eslatma: matn*",
            parse_mode="Markdown", reply_markup=MENU
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
        await update.message.reply_text(await get_weather(text), parse_mode="Markdown", reply_markup=MENU)
        context.user_data["mode"] = "ai"
        return
    if mode == "search":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await update.message.reply_text(await search_web(text), parse_mode="Markdown", reply_markup=MENU)
        context.user_data["mode"] = "ai"
        return
    if mode == "slides":
        await update.message.reply_text("⏳ Slayd va rasmlar tayyorlanmoqda, biroz kuting...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_document")
        pptx_file, error = await make_pptx(text)
        if error:
            await update.message.reply_text(error, reply_markup=MENU)
        else:
            await update.message.reply_document(
                document=pptx_file,
                filename=f"{text[:30]}.pptx",
                caption=f"📊 *{text}* bo'yicha slayd tayyor!",
                parse_mode="Markdown",
                reply_markup=MENU
            )
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
            system="Siz @Samik_1806 tomonidan yaratilgan AI yordamchisiz. Claude yoki Anthropic haqida gapirmaysiz. Kim yaratgani so'ralsa '@Samik_1806 yaratgan' deng. Foydalanuvchi qaysi tilda yozsa shu tilda javob bering. Qisqa va aniq javob bering.",
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
