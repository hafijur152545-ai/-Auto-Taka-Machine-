import os, json, hmac, hashlib, time, threading
from urllib.parse import parse_qsl
from flask import Flask, request, Response, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://auto-taka-machine.onrender.com")

@app.route('/')
def home():
    # Direct read - no send_from_directory - faster, no timeout
    for p in [os.path.join(WEBAPP_DIR, 'index.html'), os.path.join(BASE_DIR, 'webapp', 'index.html'), os.path.join(BASE_DIR, 'index.html')]:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    content = f.read()
                return Response(content, mimetype='text/html')
            except Exception as e:
                return f"Read error: {e} path={p}", 500
    return "index.html not found in any location", 404

@app.route('/<path:path>')
def static_files(path):
    # Direct read for css/js
    for base in [WEBAPP_DIR, os.path.join(BASE_DIR, 'webapp'), BASE_DIR]:
        full = os.path.join(base, path)
        if os.path.exists(full):
            if path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                with open(full, 'rb') as f:
                    ext = path.rsplit('.', 1)[-1].lower()
                    return Response(f.read(), mimetype='image/' + ('jpeg' if ext in ('jpg', 'jpeg') else ext))
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Set correct mimetype
                if path.endswith('.css'):
                    return Response(content, mimetype='text/css')
                elif path.endswith('.js'):
                    return Response(content, mimetype='application/javascript')
                else:
                    return Response(content)
            except Exception as e:
                return f"Error reading {path}: {e}", 500
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
        return "❌ BOT_TOKEN missing in Render Environment", 500
    try:
        from telegram.ext import Application, CommandHandler
        from telegram import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
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
    <h2>✅ Bot Check - V4 Direct Read</h2>
    BOT_TOKEN set: {bool(BOT_TOKEN)} (len={len(BOT_TOKEN) if BOT_TOKEN else 0})<br>
    WEBAPP_URL: {WEBAPP_URL}<br>
    BASE_DIR: {BASE_DIR}<br>
    WEBAPP_DIR: {WEBAPP_DIR} exists={os.path.exists(WEBAPP_DIR)}<br>
    BASE files: {base_files}<br>
    WEBAPP files: {webapp_files}<br>
    <br>
    <a href='/'>Home</a> | <a href='/setwebhook'>Set Webhook</a> | <a href='/check'>Check</a>
    """

# ===== ADMIN API =====
ADMIN_ID = 6560485203
DATA_FILE = os.getenv("DATA_FILE", "/tmp/atm_data.json")  # NOT inside BASE_DIR, so static route can't serve it
_lock = threading.Lock()
DEFAULTS = {"settings": {"reward_watch": 0.5, "reward_auto": 0.5, "min": {"bkash": 0, "nagad": 0, "rocket": 0, "binance": 0, "recharge": 0}, "vpn_country": ""}, "users": {}, "withdraws": []}

def load():
    try:
        with open(DATA_FILE, encoding='utf-8') as f: d = json.load(f)
    except Exception: d = {}
    for k, v in DEFAULTS.items(): d.setdefault(k, json.loads(json.dumps(v)))
    return d

def save(d):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(d, f)

def tg_user():
    # Verifies Telegram initData signature, so the ID cannot be faked
    raw = request.headers.get("X-Init-Data", "")
    if not raw or not BOT_TOKEN: return None
    try:
        p = dict(parse_qsl(raw, keep_blank_values=True))
        h = p.pop("hash", "")
        chk = "\n".join(f"{k}={v}" for k, v in sorted(p.items()))
        sec = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(hmac.new(sec, chk.encode(), hashlib.sha256).hexdigest(), h): return None
        return json.loads(p["user"])
    except Exception: return None

def is_admin(u): return bool(u) and int(u.get("id", 0)) == ADMIN_ID

def uname(u): return (u.get("first_name", "") + " " + u.get("last_name", "")).strip()

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    with _lock:
        d = load(); cur = d["settings"]
        if request.method == 'POST':
            if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
            try:
                s = request.get_json(force=True) or {}
                for k in ("reward_watch", "reward_auto"):
                    if k in s: cur[k] = max(0.0, float(s[k]))
                for k in cur["min"]:
                    if k in s.get("min", {}): cur["min"][k] = max(0.0, float(s["min"][k]))
                if "vpn_country" in s: cur["vpn_country"] = str(s["vpn_country"])[:40]
            except Exception: return jsonify(error="bad data"), 400
            save(d)
        return jsonify(cur)

@app.route('/api/register', methods=['POST'])
def api_register():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); uid = str(u["id"])
        if uid not in d["users"]:
            d["users"][uid] = {"id": u["id"], "name": uname(u), "username": u.get("username", ""), "joined": int(time.time())}
            save(d)
    return jsonify(ok=True)

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    try:
        b = request.get_json(force=True) or {}
        w = {"id": int(time.time() * 1000), "uid": u["id"], "name": uname(u), "method": str(b.get("method", ""))[:20], "number": str(b.get("number", ""))[:20], "amount": float(b.get("amount", 0)), "status": "Pending", "date": int(time.time())}
    except Exception: return jsonify(error="bad data"), 400
    with _lock:
        d = load(); d["withdraws"].insert(0, w); save(d)
    return jsonify(ok=True)

@app.route('/api/admin/data')
def api_admin_data():
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    with _lock: d = load()
    return jsonify(users=sorted(d["users"].values(), key=lambda x: -x["joined"]), withdraws=d["withdraws"])

@app.route('/api/admin/withdraw_status', methods=['POST'])
def api_admin_wstatus():
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    b = request.get_json(force=True) or {}
    if b.get("status") not in ("Approved", "Pending", "Rejected"): return jsonify(error="bad status"), 400
    with _lock:
        d = load()
        for w in d["withdraws"]:
            if w["id"] == b.get("id"): w["status"] = b["status"]
        save(d)
    return jsonify(ok=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
