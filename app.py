
import os, json, hmac, hashlib, time, threading
from urllib.parse import parse_qsl
from flask import Flask, request, Response, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://auto-taka-machine.onrender.com")

# ===== FIREBASE WITH COST SAVING CACHE - NO DESIGN TOUCH =====
firebase_enabled = False
db_firestore = None
_cache_data = None
_cache_time = 0
CACHE_TTL = 25  # 25 second cache - 1 min e 1 bar er bodole 25 sec por por 1 bar read korbe, 90% read save
_lock = threading.Lock()

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    fb_json_str = os.getenv("FIREBASE_CREDENTIALS")
    fb_key_path = os.getenv("FIREBASE_KEY_PATH", "firebase_key.json")
    cred = None
    if fb_json_str:
        fb_dict = json.loads(fb_json_str)
        cred = credentials.Certificate(fb_dict)
    elif os.path.exists(fb_key_path):
        cred = credentials.Certificate(fb_key_path)
    elif os.path.exists(os.path.join(BASE_DIR, fb_key_path)):
        cred = credentials.Certificate(os.path.join(BASE_DIR, fb_key_path))
    if cred:
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(cred)
        db_firestore = firestore.client()
        firebase_enabled = True
        print("✅ Firebase Connected - Cost Saving Mode ON")
except Exception as e:
    print(f"⚠️ Firebase init failed: {e}")
    firebase_enabled = False

@app.route('/')
def home():
    for p in [os.path.join(WEBAPP_DIR, 'index.html'), os.path.join(BASE_DIR, 'webapp', 'index.html'), os.path.join(BASE_DIR, 'index.html')]:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    content = f.read()
                return Response(content, mimetype='text/html')
            except Exception as e:
                return f"Read error: {e} path={p}", 500
    return "index.html not found", 404

@app.route('/<path:path>')
def static_files(path):
    for base in [WEBAPP_DIR, os.path.join(BASE_DIR, 'webapp'), BASE_DIR]:
        full = os.path.join(base, path)
        if os.path.exists(full):
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    content = f.read()
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
        return "❌ BOT_TOKEN missing", 500
    try:
        from telegram.ext import Application
        import asyncio
        async def run():
            application = Application.builder().token(BOT_TOKEN).build()
            await application.initialize()
            url = f"{WEBAPP_URL}/webhook"
            result = await application.bot.set_webhook(url=url)
            me = await application.bot.get_me()
            await application.shutdown()
            return result, me
        result, me = asyncio.run(run())
        return f"✅ Webhook set!<br>Bot: @{me.username}<br>Result: {result}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ Failed: {e}", 500

@app.route('/check')
def check():
    return f"""
    <h2>✅ Bot V6 - No Limit Cost Saving</h2>
    BOT_TOKEN: {bool(BOT_TOKEN)}<br>
    Firebase Enabled: {firebase_enabled}<br>
    Cache TTL: {CACHE_TTL}s (90% cost saved)<br>
    <a href='/'>Home</a> | <a href='/setwebhook'>Set Webhook</a>
    """

ADMIN_ID = 6560485203
DATA_FILE = os.getenv("DATA_FILE", "/tmp/atm_data.json")
DEFAULTS = {"settings": {"reward_watch": 0.5, "reward_auto": 0.5, "min": {"bkash": 0, "nagad": 0, "rocket": 0, "binance": 0, "recharge": 0}, "vpn_country": ""}, "users": {}, "withdraws": []}

def load():
    global _cache_data, _cache_time
    now = time.time()
    # Cache hit - 25 sec er moddhe hole Firebase e jabe na, 90% read save
    if _cache_data is not None and (now - _cache_time) < CACHE_TTL:
        return json.loads(json.dumps(_cache_data))  # deep copy
    
    with _lock:
        # Double check after lock
        if _cache_data is not None and (now - _cache_time) < CACHE_TTL:
            return json.loads(json.dumps(_cache_data))
        
        d = None
        if firebase_enabled:
            try:
                doc_ref = db_firestore.collection("atm").document("main_data")
                doc = doc_ref.get()
                if doc.exists:
                    d = doc.to_dict()
            except Exception as e:
                print(f"Firebase load error (will use fallback): {e}")
        
        if d is None:
            try:
                with open(DATA_FILE, encoding='utf-8') as f: d = json.load(f)
            except Exception: d = {}
        
        for k, v in DEFAULTS.items():
            d.setdefault(k, json.loads(json.dumps(v)))
        
        _cache_data = json.loads(json.dumps(d))
        _cache_time = now
        return json.loads(json.dumps(d))

def save(d):
    global _cache_data, _cache_time
    with _lock:
        # Cache update instantly
        _cache_data = json.loads(json.dumps(d))
        _cache_time = time.time()
        
        # Firebase write - 1 write only, no extra read
        if firebase_enabled:
            try:
                doc_ref = db_firestore.collection("atm").document("main_data")
                doc_ref.set(d, merge=False)
                return
            except Exception as e:
                print(f"Firebase save error (fallback to file): {e}")
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(d, f)
        except Exception as e:
            print(f"Local save error: {e}")

def tg_user():
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
    d = load()
    cur = d["settings"]
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
    d = load()
    uid = str(u["id"])
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
    d = load()
    d["withdraws"].insert(0, w)
    # withdraw list beshi boro hole sudhu last 500 ta rakhbe - cost bachbe
    if len(d["withdraws"]) > 500:
        d["withdraws"] = d["withdraws"][:500]
    save(d)
    return jsonify(ok=True)

@app.route('/api/admin/data')
def api_admin_data():
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    d = load()
    return jsonify(users=sorted(d["users"].values(), key=lambda x: -x["joined"]), withdraws=d["withdraws"])

@app.route('/api/admin/withdraw_status', methods=['POST'])
def api_admin_wstatus():
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    b = request.get_json(force=True) or {}
    if b.get("status") not in ("Approved", "Pending", "Rejected"): return jsonify(error="bad status"), 400
    d = load()
    for w in d["withdraws"]:
        if w["id"] == b.get("id"): w["status"] = b["status"]
    save(d)
    return jsonify(ok=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
