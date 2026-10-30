import os
from flask import Flask, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://auto-taka-machine.onrender.com")

# --- Telegram ---
try:
    from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler
    HAS_TG = True
except:
    HAS_TG = False

async def start(update, context):
    kb = [[InlineKeyboardButton("🤖 Auto Taka Machine 🔥 Open", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}!\n\n🔥 Auto Taka Machine Ready! Open:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

def get_app():
    if not HAS_TG or not BOT_TOKEN:
        return None
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    return application

@app.route('/')
def home():
    # Try multiple locations for index.html
    possible = [
        os.path.join(WEBAPP_DIR, 'index.html'),
        os.path.join(BASE_DIR, 'webapp', 'index.html'),
        os.path.join(BASE_DIR, 'index.html'),
    ]
    for p in possible:
        if os.path.exists(p):
            dir_name = os.path.dirname(p)
            return send_from_directory(dir_name, 'index.html')
    
    # Debug if not found
    debug = f"BASE_DIR={BASE_DIR}<br>WEBAPP_DIR={WEBAPP_DIR}<br>"
    debug += f"BASE files: {os.listdir(BASE_DIR)[:20]}<br>"
    if os.path.exists(WEBAPP_DIR):
        debug += f"WEBAPP files: {os.listdir(WEBAPP_DIR)[:20]}<br>"
    return f"<h3>index.html not found</h3>{debug}", 404

@app.route('/<path:path>')
def files(path):
    # Serve any file from webapp folder
    if os.path.exists(os.path.join(WEBAPP_DIR, path)):
        return send_from_directory(WEBAPP_DIR, path)
    if os.path.exists(os.path.join(BASE_DIR, path)):
        return send_from_directory(BASE_DIR, path)
    if os.path.exists(os.path.join(BASE_DIR, 'webapp', path)):
        return send_from_directory(os.path.join(BASE_DIR, 'webapp'), path)
    return f"File not found: {path}", 404

@app.route('/webhook', methods=['POST'])
def webhook():
    if not BOT_TOKEN:
        return "BOT_TOKEN missing", 500
    if not HAS_TG:
        return "telegram lib missing", 500
    try:
        import asyncio
        data = request.get_json(force=True)
        application = get_app()
        async def process():
            await application.initialize()
            update = Update.de_json(data, application.bot)
            await application.process_update(update)
            await application.shutdown()
        asyncio.run(process())
        return "ok", 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"Error: {e}", 500

@app.route('/setwebhook')
def set_webhook():
    if not BOT_TOKEN:
        return "BOT_TOKEN missing - set in Render Environment", 500
    if not HAS_TG:
        return "telegram lib missing", 500
    try:
        import asyncio
        async def set_hook():
            application = get_app()
            await application.initialize()
            url = f"{WEBAPP_URL}/webhook"
            result = await application.bot.set_webhook(url=url)
            info = await application.bot.get_me()
            await application.shutdown()
            return result, info
        result, info = asyncio.run(set_hook())
        return f"✅ Webhook set!<br>Bot: @{info.username}<br>URL: {WEBAPP_URL}/webhook<br>Result: {result}<br><br><a href='/'>Go to App</a>"
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"❌ Failed: {e}", 500

@app.route('/check')
def check():
    files_base = os.listdir(BASE_DIR)[:20] if os.path.exists(BASE_DIR) else []
    files_webapp = os.listdir(WEBAPP_DIR)[:20] if os.path.exists(WEBAPP_DIR) else []
    return f"""
    <h2>Check</h2>
    BOT_TOKEN: {bool(BOT_TOKEN)} len={len(BOT_TOKEN) if BOT_TOKEN else 0}<br>
    WEBAPP_URL: {WEBAPP_URL}<br>
    BASE_DIR: {BASE_DIR}<br>
    WEBAPP_DIR: {WEBAPP_DIR}<br>
    BASE files: {files_base}<br>
    WEBAPP files: {files_webapp}<br>
    <a href='/setwebhook'>Set Webhook</a> | <a href='/'>Home</a>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
