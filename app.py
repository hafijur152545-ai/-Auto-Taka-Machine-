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

from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🤖 Auto Taka Machine 🔥 Open", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}!\n\n🔥 Auto Taka Machine Ready!\nOpen the app:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# Global Application - Initialize ONCE
application = None
main_loop = None

if BOT_TOKEN:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    # Create main event loop and initialize
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)
    try:
        main_loop.run_until_complete(application.initialize())
        print("✅ Bot initialized successfully")
        # Auto set webhook on startup
        webhook_url = f"{WEBAPP_URL}/webhook"
        main_loop.run_until_complete(application.bot.set_webhook(url=webhook_url))
        print(f"✅ Webhook auto-set to {webhook_url}")
    except Exception as e:
        print(f"Init Error: {e}")

@app.route('/')
def home():
    return send_from_directory(WEBAPP_DIR, 'index.html')

@app.route('/<path:path>')
def files(path):
    return send_from_directory(WEBAPP_DIR, path)

@app.route('/webhook', methods=['POST'])
def webhook():
    if not application or not BOT_TOKEN or not main_loop:
        return "Bot not initialized", 500
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        # Use main_loop, don't create new one, don't close it
        main_loop.run_until_complete(application.process_update(update))
        return "ok", 200
    except Exception as e:
        print(f"Webhook Error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}", 500

@app.route('/setwebhook')
def set_webhook():
    if not application or not BOT_TOKEN or not main_loop:
        return "BOT_TOKEN missing", 500
    try:
        webhook_url = f"{WEBAPP_URL}/webhook"
        result = main_loop.run_until_complete(application.bot.set_webhook(url=webhook_url))
        info = main_loop.run_until_complete(application.bot.get_me())
        return f"✅ Webhook set!<br>Bot: @{info.username}<br>URL: {webhook_url}<br>Result: {result}<br><br>Now send /start in Telegram"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ Failed: {e}", 500

@app.route('/check')
def check():
    token_len = len(BOT_TOKEN) if BOT_TOKEN else 0
    return f"""
    <h2>🔍 Bot Check</h2>
    BOT_TOKEN exists: {bool(BOT_TOKEN)}<br>
    BOT_TOKEN length: {token_len}<br>
    WEBAPP_URL: {WEBAPP_URL}<br>
    App initialized: {application is not None}<br>
    Loop exists: {main_loop is not None}<br>
    WEBAPP_DIR: {WEBAPP_DIR}<br>
    Files: {os.listdir(WEBAPP_DIR) if os.path.exists(WEBAPP_DIR) else 'NOT FOUND'}<br>
    <br><a href='/setwebhook'>Set Webhook</a><br>
    <a href='/'>Go to App</a>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
