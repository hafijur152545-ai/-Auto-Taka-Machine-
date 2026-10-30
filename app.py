import os
from flask import Flask, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://auto-taka-machine.onrender.com")

@app.route('/')
def home():
    # Most robust way - try all possible paths
    index_path = os.path.join(WEBAPP_DIR, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(WEBAPP_DIR, 'index.html')
    # fallback
    if os.path.exists(os.path.join(BASE_DIR, 'index.html')):
        return send_from_directory(BASE_DIR, 'index.html')
    return f"<h3>index.html not found</h3>BASE={BASE_DIR}<br>WEBAPP={WEBAPP_DIR}<br>BASE files={os.listdir(BASE_DIR)}<br>WEBAPP exists={os.path.exists(WEBAPP_DIR)}", 404

@app.route('/<path:path>')
def static_files(path):
    # Try webapp first
    full = os.path.join(WEBAPP_DIR, path)
    if os.path.exists(full):
        return send_from_directory(WEBAPP_DIR, path)
    full2 = os.path.join(BASE_DIR, path)
    if os.path.exists(full2):
        return send_from_directory(BASE_DIR, path)
    return f"File not found: {path}", 404

@app.route('/webhook', methods=['POST'])
def webhook():
    if not BOT_TOKEN:
        return "BOT_TOKEN missing", 500
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler
        from telegram import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
        import asyncio

        async def start(update, context):
            kb = [[InlineKeyboardButton("🤖 Auto Taka Machine 🔥 Open", web_app=WebAppInfo(url=WEBAPP_URL))]]
            await update.message.reply_text(f"Hello {update.effective_user.first_name}! Open:", reply_markup=InlineKeyboardMarkup(kb))

        data = request.get_json(force=True)
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))

        async def process():
            await application.initialize()
            update = Update.de_json(data, application.bot)
            await application.process_update(update)
            await application.shutdown()

        asyncio.run(process())
        return "ok", 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Webhook Error: {e}", 500

@app.route('/setwebhook')
def set_webhook():
    if not BOT_TOKEN:
        return "❌ BOT_TOKEN missing in Render Environment Variables", 500
    try:
        from telegram.ext import Application
        from telegram import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import CommandHandler
        import asyncio

        async def start(update, context):
            kb = [[InlineKeyboardButton("🤖 Auto Taka Machine 🔥 Open", web_app=WebAppInfo(url=WEBAPP_URL))]]
            await update.message.reply_text("Hello! Open:", reply_markup=InlineKeyboardMarkup(kb))

        async def run():
            application = Application.builder().token(BOT_TOKEN).build()
            application.add_handler(CommandHandler("start", start))
            await application.initialize()
            url = f"{WEBAPP_URL}/webhook"
            result = await application.bot.set_webhook(url=url)
            me = await application.bot.get_me()
            await application.shutdown()
            return result, me

        result, me = asyncio.run(run())
        return f"✅ Webhook set!<br>Bot: @{me.username}<br>URL: {WEBAPP_URL}/webhook<br>Result: {result}<br><br><a href='/'>Go to App</a>"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ Failed: {e}", 500

@app.route('/check')
def check():
    base_files = []
    webapp_files = []
    try:
        base_files = os.listdir(BASE_DIR)[:20]
    except: pass
    try:
        webapp_files = os.listdir(WEBAPP_DIR)[:20]
    except: pass
    return f"""
    <h2>✅ Bot Check - V3 Minimal</h2>
    BOT_TOKEN set: {bool(BOT_TOKEN)} (len={len(BOT_TOKEN) if BOT_TOKEN else 0})<br>
    WEBAPP_URL: {WEBAPP_URL}<br>
    BASE_DIR: {BASE_DIR}<br>
    WEBAPP_DIR: {WEBAPP_DIR} exists={os.path.exists(WEBAPP_DIR)}<br>
    BASE files: {base_files}<br>
    WEBAPP files: {webapp_files}<br>
    <br>
    <a href='/'>Home</a> | <a href='/setwebhook'>Set Webhook</a> | <a href='/check'>Check</a>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
