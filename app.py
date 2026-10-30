
import os
import asyncio
import logging
from flask import Flask, request, jsonify, send_from_directory
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://auto-taka-machine.onrender.com")

if not BOT_TOKEN:
    logger.warning("BOT_TOKEN not set!")

app = Flask(__name__)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

telegram_app = None

async def init_bot():
    global telegram_app
    try:
        telegram_app = Application.builder().token(BOT_TOKEN).build()
        telegram_app.add_handler(CommandHandler("start", start_command))
        await telegram_app.initialize()
        await telegram_app.start()
        if WEBAPP_URL:
            webhook_url = f"{WEBAPP_URL}/webhook"
            await telegram_app.bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook set to {webhook_url}")
        logger.info("✅ Bot initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Bot init error: {e}")
        return False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [[InlineKeyboardButton("💰 Open Auto Taka Machine", web_app=WebAppInfo(url=WEBAPP_URL))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🤖 *Auto Taka Machine* 🔥\n\nWelcome! Click below to open premium mini app and start earning!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Start error: {e}")

try:
    loop.run_until_complete(init_bot())
except Exception as e:
    logger.error(f"Startup error: {e}")

# --- FIXED ROUTES FOR MULTI FILE ---
@app.route("/")
def index():
    return send_from_directory("webapp", "index.html")

# Serve CSS, JS, etc from webapp folder when requested from root
@app.route("/<path:path>")
def serve_static(path):
    # Try webapp folder first
    webapp_path = os.path.join("webapp", path)
    if os.path.exists(webapp_path):
        return send_from_directory("webapp", path)
    # Try root
    if os.path.exists(path):
        return send_from_directory(".", path)
    return f"File not found: {path}", 404

@app.route("/webapp/<path:path>")
def serve_webapp(path):
    return send_from_directory("webapp", path)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, telegram_app.bot)
        loop.create_task(telegram_app.process_update(update))
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

@app.route("/setwebhook")
def set_webhook():
    try:
        async def set_wh():
            webhook_url = f"{WEBAPP_URL}/webhook"
            await telegram_app.bot.set_webhook(url=webhook_url)
            return webhook_url
        url = loop.run_until_complete(set_wh())
        return jsonify({"status": "✅ Webhook set successfully", "url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/check")
def check():
    files = {
        "index.html": os.path.exists("webapp/index.html"),
        "style.css": os.path.exists("webapp/style.css"),
        "script.js": os.path.exists("webapp/script.js"),
        "light-effect.css": os.path.exists("webapp/light-effect.css"),
        "light-effect.js": os.path.exists("webapp/light-effect.js"),
    }
    return jsonify({
        "BOT_TOKEN_exists": bool(BOT_TOKEN),
        "BOT_TOKEN_length": len(BOT_TOKEN) if BOT_TOKEN else 0,
        "WEBAPP_URL": WEBAPP_URL,
        "App_initialized": telegram_app is not None,
        "files": files,
        "message": "All files should be True"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
