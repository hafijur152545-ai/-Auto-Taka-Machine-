
import os
import threading
from flask import Flask, send_from_directory
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

app = Flask(__name__, static_folder='webapp')

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app.onrender.com")

@app.route('/')
def home(): 
    return send_from_directory('webapp','index.html')

@app.route('/<path:path>')
def files(path): 
    return send_from_directory('webapp', path)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🤖 Auto Taka Machine 🔥 Open", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}!\n\n🔥 Auto Taka Machine Ready!\n\nToday Ads: 0\nMain Balance: 10.20 TK\n\nনিচের বাটনে ক্লিক করে App Open করো:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

def run_bot():
    if not BOT_TOKEN:
        print("BOT_TOKEN missing! Bot will not start.")
        return
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    print("Bot polling started...")
    application.run_polling()

if BOT_TOKEN:
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
