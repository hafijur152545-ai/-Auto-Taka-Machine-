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
from telegram.ext import Application, CommandHandler

async def start(update, context):
    kb = [[InlineKeyboardButton("🤖 Auto Taka Machine 🔥 Open", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}!\n\n🔥 Auto Taka Machine Ready!\nOpen the app:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

def get_application():
    if not BOT_TOKEN:
        return None
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    return application

@app.route('/')
def home():
    return send_from_directory(WEBAPP_DIR, 'index.html')

@app.route('/<path:path>')
def files(path):
    return send_from_directory(WEBAPP_DIR, path)

@app.route('/webhook', methods=['POST'])
def webhook():
    if not BOT_TOKEN:
        return "BOT_TOKEN missing", 500
    try:
        data = request.get_json(force=True)
        application = get_application()
        if not application:
            return "No app", 500
        
        async def process():
            await application.initialize()
            update = Update.de_json(data, application.bot)
            await application.process_update(update)
            await application.shutdown()
        
        asyncio.run(process())
        return "ok", 200
    except Exception as e:
        print(f"Webhook Error: {e}")
        import traceback; traceback.print_exc()
        return f"Error: {e}", 500

@app.route('/setwebhook')
def set_webhook():
    if not BOT_TOKEN:
        return "BOT_TOKEN missing", 500
    try:
        async def set_hook():
            application = get_application()
            await application.initialize()
            webhook_url = f"{WEBAPP_URL}/webhook"
            result = await application.bot.set_webhook(url=webhook_url)
            info = await application.bot.get_me()
            await application.shutdown()
            return result, info
        
        result, info = asyncio.run(set_hook())
        return f"✅ Webhook set!<br>Bot: @{info.username}<br>URL: {WEBAPP_URL}/webhook<br>Result: {result}"
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"❌ Failed: {e}", 500

@app.route('/check')
def check():
    token_len = len(BOT_TOKEN) if BOT_TOKEN else 0
    files_list = os.listdir(WEBAPP_DIR) if os.path.exists(WEBAPP_DIR) else 'NOT FOUND'
    return f"""
    <h2>🔍 Bot Check</h2>
    BOT_TOKEN exists: {bool(BOT_TOKEN)}<br>
    Length: {token_len}<br>
    WEBAPP_URL: {WEBAPP_URL}<br>
    WEBAPP_DIR: {WEBAPP_DIR}<br>
    Files: {files_list}<br>
    <br><a href='/setwebhook'>Set Webhook</a> | <a href='/'>App</a>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
