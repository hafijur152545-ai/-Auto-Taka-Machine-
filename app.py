import os, threading, asyncio
from flask import Flask, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')

if not os.path.exists(WEBAPP_DIR):
    WEBAPP_DIR = BASE_DIR

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://auto-taka-machine.onrender.com")

@app.route('/')
def home():
    return send_from_directory(WEBAPP_DIR, 'index.html')

@app.route('/<path:path>')
def files(path):
    return send_from_directory(WEBAPP_DIR, path)

from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🤖 Auto Taka Machine 🔥 Open", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(f"Hello {update.effective_user.first_name}!", reply_markup=InlineKeyboardMarkup(kb))

def run_bot():
    if not BOT_TOKEN:
        print("BOT_TOKEN missing")
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        print("Bot polling started...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"Bot Error: {e}")

if BOT_TOKEN:
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
