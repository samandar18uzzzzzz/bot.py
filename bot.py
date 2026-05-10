import os
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Kalitlar Railway environment variables dan oqiladi
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Har foydalanuvchi uchun suhbat tarixi
user_histories = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    # Tarix yo'q bo'lsa yangi yarat
    if user_id not in user_histories:
        user_histories[user_id] = []

    # Foydalanuvchi xabarini qo'sh
    user_histories[user_id].append({
        "role": "user",
        "content": user_text
    })

    # Yozmoqda... ko'rsatish
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        # Claude API ga yuborish
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system="Siz foydali AI yordamchisiz. Foydalanuvchi qaysi tilda yozsa, shu tilda javob bering — o'zbek, rus yoki ingliz. Qisqa va aniq javob bering.",
            messages=user_histories[user_id]
        )

        reply = response.content[0].text

        # Bot javobini tarixga qo'sh
        user_histories[user_id].append({
            "role": "assistant",
            "content": reply
        })

        # Tarixni 20 xabargacha chekla (xotira tejash)
        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]

        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text("❌ Xato yuz berdi. Qayta urinib ko'ring.")
        print(f"Xato: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot ishga tushdi! ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
