
import os
import asyncio
from flask import Flask, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')
if not os.path.exists(WEBAPP_DIR):
    WEBAPP_DIR = BASE_DIR

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://auto-taka-machine.onrender.com")

# === Telegram Bot Setup (Webhook Mode) ===
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🤖 Auto Taka Machine 🔥 Open", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}!\n\n🔥 Auto Taka Machine Ready!\nOpen the app:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# Global Application
application = None
if BOT_TOKEN:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    print("Bot application created (Webhook mode)")

@app.route('/')
def home():
    return send_from_directory(WEBAPP_DIR, 'index.html')

@app.route('/<path:path>')
def files(path):
    return send_from_directory(WEBAPP_DIR, path)

@app.route('/webhook', methods=['POST'])
def webhook():
    if not application or not BOT_TOKEN:
        return "Bot not configured", 500
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.process_update(update))
        loop.close()
        return "ok", 200
    except Exception as e:
        print(f"Webhook Error: {e}")
        return f"Error: {e}", 500

@app.route('/setwebhook')
def set_webhook():
    if not application or not BOT_TOKEN:
        return "BOT_TOKEN missing", 500
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        webhook_url = f"{WEBAPP_URL}/webhook"
        result = loop.run_until_complete(application.bot.set_webhook(url=webhook_url))
        loop.close()
        return f"✅ Webhook set successfully!<br>URL: {webhook_url}<br>Result: {result}<br><br>Now go to Telegram and send /start"
    except Exception as e:
        return f"Failed to set webhook: {e}", 500

@app.route('/deletewebhook')
def delete_webhook():
    if not application or not BOT_TOKEN:
        return "BOT_TOKEN missing", 500
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(application.bot.delete_webhook())
        loop.close()
        return f"Webhook deleted: {result}"
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
