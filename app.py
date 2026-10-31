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
            try:
                if context.args and context.args[0].isdigit(): register_ref(update.effective_user.id, context.args[0])
            except Exception: pass
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

@app.route('/dbcheck')
def dbcheck():
    with _lock:
        try:
            d = load()
            return (f"Storage: <b>{STORAGE}</b><br>Firebase error: {FB_ERROR or 'none'}<br>"
                    f"Users: {len(d['users'])} | Withdraws: {len(d['withdraws'])}")
        except Exception as e:
            return f"Storage error: {e}", 500

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
AD_MIN_SECONDS = float(os.getenv("AD_MIN_SECONDS", "15"))  # server-side check: ad reward only after this many seconds
_lock = threading.Lock()
DEFAULT_GUIDELINES = ("1. Watch ads daily to earn 0.50 TK per ad\n"
                      "2. Use VPN from KAJER VPN button for more ads\n"
                      "3. Refer friends to get 10% bonus\n"
                      "4. Confirm Pending Balance after 500 ads\n"
                      "5. Contact admin for support")
DEFAULTS = {"settings": {"reward_watch": 0.5, "reward_auto": 0.10, "limit_watch": 100, "limit_auto": 100,
                         "notice": "📢 VPN diye kaj korbe",
                         "country_notice": "⚠️ {country} VPN/Proxy on korun, tarpor ad dekhun. Apnar current country: {current}",
                         "ref_bonus": 10,
                         "min": {"bkash": 0, "nagad": 0, "rocket": 0, "binance": 0, "recharge": 0}, "vpn_country": "",
                         "bot_guidelines": DEFAULT_GUIDELINES,
                         "home_notice": "",
                         "usdt_rate": 123.0,
                         "payment_methods": {"bkash": True, "nagad": True, "rocket": True, "binance": True, "recharge": True}},
            "users": {}, "withdraws": [], "refs": {}}

# ---------- storage: Firebase Firestore (permanent) with JSON-file fallback ----------
# Set FIREBASE_CREDENTIALS in Render (service-account JSON). Everything is kept in memory (one gunicorn worker)
# and every change is written to Firestore, so a restart / redeploy never loses balances.
_db = None
_cache = None
_hashes = {"meta": "", "users": {}, "withdraws": {}}
STORAGE = "file"
FB_ERROR = ""

def _init_firebase():
    global _db, STORAGE, FB_ERROR
    raw = (os.getenv("FIREBASE_CREDENTIALS") or "").strip()
    if not raw: FB_ERROR = "FIREBASE_CREDENTIALS not set"; return
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        if raw.startswith("{"): info = json.loads(raw)
        elif os.path.exists(raw): info = raw
        else:
            import base64
            info = json.loads(base64.b64decode(raw).decode("utf-8"))
        if not firebase_admin._apps: firebase_admin.initialize_app(credentials.Certificate(info))
        _db = firestore.client(); STORAGE = "firestore"; FB_ERROR = ""
    except Exception as e:
        import traceback; traceback.print_exc()
        _db = None; FB_ERROR = str(e)[:200]

def _js(x): return json.dumps(x, sort_keys=True, default=str)

def _boot_load():
    d = {}
    if _db is not None:
        try:
            m = _db.collection("atm_meta").document("main").get()
            md = m.to_dict() if m.exists else {}
            d["settings"] = md.get("settings", {}); d["refs"] = md.get("refs", {})
            d["users"] = {x.id: x.to_dict() for x in _db.collection("atm_users").stream()}
            d["withdraws"] = sorted([x.to_dict() for x in _db.collection("atm_withdraws").stream()], key=lambda w: -int(w.get("id", 0)))
            empty = not md and not d["users"] and not d["withdraws"]
            if empty:  # first run on Firebase: bring over the old JSON file if there is one
                try:
                    with open(DATA_FILE, encoding='utf-8') as f: old = json.load(f)
                    if old.get("users") or old.get("withdraws"): d = old
                except Exception: pass
            return d
        except Exception:
            import traceback; traceback.print_exc()
            raise
    try:
        with open(DATA_FILE, encoding='utf-8') as f: d = json.load(f)
    except Exception: d = {}
    return d

def load():
    global _cache
    if _cache is None:
        if _db is None and STORAGE == "file" and not FB_ERROR: _init_firebase()
        _cache = _boot_load()
        for k, v in DEFAULTS.items(): _cache.setdefault(k, json.loads(json.dumps(v)))
        _hashes["meta"] = ""; _hashes["users"] = {}; _hashes["withdraws"] = {}
        if _db is not None: save(_cache)  # writes anything that was imported
    for k, v in DEFAULTS.items(): _cache.setdefault(k, json.loads(json.dumps(v)))
    return _cache

def save(d):
    global _cache
    _cache = d
    if _db is None:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f: json.dump(d, f)
        os.replace(tmp, DATA_FILE); return
    try:
        batch = _db.batch(); n = 0; pend = []
        def put(coll, doc, data, store, key):
            nonlocal batch, n
            h = _js(data)
            if store.get(key) == h: return
            batch.set(_db.collection(coll).document(doc), data); pend.append((store, key, h)); n += 1
            if n >= 400:
                batch.commit(); [s.__setitem__(k, v) for s, k, v in pend]; pend.clear(); batch = _db.batch(); n = 0
        meta = {"settings": d["settings"], "refs": d["refs"]}; mh = _js(meta)
        if _hashes["meta"] != mh:
            batch.set(_db.collection("atm_meta").document("main"), meta); pend.append((_hashes, "meta", mh)); n += 1
        for uid, rec in d["users"].items(): put("atm_users", str(uid), rec, _hashes["users"], uid)
        for w in d["withdraws"]: put("atm_withdraws", str(w["id"]), w, _hashes["withdraws"], str(w["id"]))
        if n: batch.commit()
        for s, k, v in pend: s[k] = v
    except Exception:
        import traceback; traceback.print_exc()  # kept in memory; the next save retries the same changes

def settings_of(d):
    cur = d["settings"]
    for k, v in DEFAULTS["settings"].items():
        if k == "min":
            cur.setdefault("min", {})
            for mk, mv in v.items(): cur["min"].setdefault(mk, mv)
        elif k == "payment_methods":
            cur.setdefault("payment_methods", {})
            for mk, mv in v.items():
                cur["payment_methods"].setdefault(mk, mv)
        else: cur.setdefault(k, v)
    return cur

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

# ---------- per-user account (server side, so every Telegram ID has its own real balance) ----------
def today_key():
    import datetime
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=6)).strftime("%Y-%m-%d")  # Bangladesh day

def new_bal():
    return {"main": 0.0, "pending": 0.0, "today_ads": 0, "total_ads": 0, "watch_today": 0, "auto_today": 0, "day": today_key()}

def roll(rec):
    b = rec["bal"]
    if b.get("day") != today_key(): b.update(day=today_key(), today_ads=0, watch_today=0, auto_today=0)

def state(rec):
    roll(rec); b = rec["bal"]
    return {"main": round(b["main"], 2), "pending": round(b["pending"], 2), "today_ads": b["today_ads"], "total_ads": b["total_ads"],
            "watch_today": b["watch_today"], "auto_today": b["auto_today"]}

def ensure_user(d, u):
    uid = str(u["id"]); rec = d["users"].get(uid)
    if not rec:
        rec = {"id": u["id"], "name": uname(u), "username": u.get("username", ""), "joined": int(time.time())}
        d["users"][uid] = rec
    rec["name"] = uname(u) or rec.get("name", ""); rec["username"] = u.get("username", "")
    if "bal" not in rec and not rec.get("ref") and d["refs"].get(uid) and d["refs"][uid] != uid: rec["ref"] = d["refs"][uid]
    if "bal" not in rec: rec["bal"] = new_bal()
    return rec

def register_ref(uid, ref):
    uid, ref = str(uid), str(ref)
    if uid == ref: return
    with _lock:
        d = load(); rec = d["users"].get(uid)
        if (rec and "bal" in rec and rec.get("ref") is not None) or uid in d["refs"] or ref not in d["users"]: return
        if rec and "bal" in rec and rec["bal"].get("total_ads", 0) > 0: return
        d["refs"][uid] = ref
        if rec and not rec.get("ref"): rec["ref"] = ref
        save(d)

def ref_stats(d, uid):
    uid = str(uid)
    cnt = sum(1 for r in d["users"].values() if r.get("ref") == uid)
    return {"count": cnt, "earned": round(d["users"].get(uid, {}).get("ref_earned", 0), 2)}

def user_withdraws(d, uid):
    return [{"id": w["id"], "method": w["method"], "number": w["number"], "amount": w["amount"], "status": w["status"], "date": w["date"]}
            for w in d["withdraws"] if str(w["uid"]) == str(uid)][:50]

# ---------- country check ----------
CNAME = {"US": "United States", "AU": "Australia", "BD": "Bangladesh", "IN": "India", "GB": "United Kingdom", "CA": "Canada", "DE": "Germany",
         "SG": "Singapore", "MY": "Malaysia", "AE": "United Arab Emirates", "SA": "Saudi Arabia", "FR": "France", "NL": "Netherlands",
         "JP": "Japan", "PK": "Pakistan", "NZ": "New Zealand", "IE": "Ireland", "SE": "Sweden", "CH": "Switzerland", "IT": "Italy", "ES": "Spain",
         "RU": "Russia", "BR": "Brazil", "MX": "Mexico", "ZA": "South Africa", "KR": "South Korea", "CN": "China", "ID": "Indonesia",
         "PH": "Philippines", "VN": "Vietnam", "TH": "Thailand", "TR": "Turkey", "EG": "Egypt", "NG": "Nigeria", "AR": "Argentina",
         "CL": "Chile", "CO": "Colombia", "PE": "Peru", "BD": "Bangladesh", "LK": "Sri Lanka", "NP": "Nepal", "BN": "Brunei",
         "HK": "Hong Kong", "TW": "Taiwan", "IL": "Israel", "PT": "Portugal", "AT": "Austria", "BE": "Belgium", "DK": "Denmark",
         "FI": "Finland", "NO": "Norway", "PL": "Poland", "CZ": "Czech Republic", "GR": "Greece", "HU": "Hungary", "RO": "Romania",
         "BG": "Bulgaria", "HR": "Croatia", "SK": "Slovakia", "SI": "Slovenia", "EE": "Estonia", "LV": "Latvia", "LT": "Lithuania",
         "UA": "Ukraine", "BY": "Belarus", "KZ": "Kazakhstan", "UZ": "Uzbekistan", "QA": "Qatar", "KW": "Kuwait", "BH": "Bahrain",
         "OM": "Oman", "JO": "Jordan", "LB": "Lebanon", "IQ": "Iraq", "IR": "Iran", "AF": "Afghanistan", "MM": "Myanmar",
         "KH": "Cambodia", "LA": "Laos", "MO": "Macau"}
ALIAS = {v.lower(): k.lower() for k, v in CNAME.items()}
ALIAS.update({"usa": "us", "america": "us", "united states of america": "us", "uk": "gb", "england": "gb", "britain": "gb", "uae": "ae",
              "korea": "kr", "south korea": "kr", "czechia": "cz", "hong kong": "hk", "macau": "mo"})

# Country flag emojis (rendered in Telegram WebApp)
FLAG = {"US":"🇺🇸","CA":"🇨🇦","GB":"🇬🇧","AU":"🇦🇺","BD":"🇧🇩","IN":"🇮🇳","DE":"🇩🇪","SG":"🇸🇬","MY":"🇲🇾","AE":"🇦🇪",
        "SA":"🇸🇦","FR":"🇫🇷","NL":"🇳🇱","JP":"🇯🇵","PK":"🇵🇰","NZ":"🇳🇿","IE":"🇮🇪","SE":"🇸🇪","CH":"🇨🇭","IT":"🇮🇹",
        "ES":"🇪🇸","RU":"🇷🇺","BR":"🇧🇷","MX":"🇲🇽","ZA":"🇿🇦","KR":"🇰🇷","CN":"🇨🇳","ID":"🇮🇩","PH":"🇵🇭","VN":"🇻🇳",
        "TH":"🇹🇭","TR":"🇹🇷","EG":"🇪🇬","NG":"🇳🇬","AR":"🇦🇷","CL":"🇨🇱","CO":"🇨🇴","PE":"🇵🇪","LK":"🇱🇰","NP":"🇳🇵",
        "BN":"🇧🇳","HK":"🇭🇰","TW":"🇹🇼","IL":"🇮🇱","PT":"🇵🇹","AT":"🇦🇹","BE":"🇧🇪","DK":"🇩🇰","FI":"🇫🇮","NO":"🇳🇴",
        "PL":"🇵🇱","CZ":"🇨🇿","GR":"🇬🇷","HU":"🇭🇺","RO":"🇷🇴","BG":"🇧🇬","HR":"🇭🇷","SK":"🇸🇰","SI":"🇸🇮","EE":"🇪🇪",
        "LV":"🇱🇻","LT":"🇱🇹","UA":"🇺🇦","BY":"🇧🇾","KZ":"🇰🇿","UZ":"🇺🇿","QA":"🇶🇦","KW":"🇰🇼","BH":"🇧🇭","OM":"🇴🇲",
        "JO":"🇯🇴","LB":"🇱🇧","IQ":"🇮🇶","IR":"🇮🇷","AF":"🇦🇫","MM":"🇲🇲","KH":"🇰🇭","LA":"🇱🇦","MO":"🇲🇴"}

# Country -> acceptable phone timezones (IANA). The user's phone timezone must match one of these
# for at least one allowed country, otherwise the ad is blocked (even if the IP matches via VPN).
COUNTRY_TZ = {
    "US": ["America/New_York","America/Detroit","America/Kentucky/Louisville","America/Kentucky/Monticello",
           "America/Indiana/Indianapolis","America/Indiana/Vincennes","America/Indiana/Winamac","America/Indiana/Marengo",
           "America/Indiana/Petersburg","America/Indiana/Vevay","America/Chicago","America/Menominee",
           "America/North_Dakota/Center","America/North_Dakota/New_Salem","America/North_Dakota/Beulah",
           "America/Denver","America/Boise","America/Phoenix","America/Los_Angeles","America/Metlakatla",
           "America/Anchorage","America/Juneau","America/Sitka","America/Yakutat","America/Nome","America/Adak",
           "Pacific/Honolulu","US/Eastern","US/Central","US/Mountain","US/Pacific","US/Alaska","US/Hawaii",
           "US/Arizona","US/East-Indiana","US/Indiana-Starke","US/Michigan"],
    "CA": ["America/Toronto","America/Vancouver","America/Halifax","America/Edmonton","America/Winnipeg",
           "America/St_Johns","America/Regina","America/Swift_Current","America/Moncton","America/Blanc-Sablon",
           "America/Glace_Bay","America/Goose_Bay","America/Rainy_River","America/Atikokan","America/Fort_Nelson",
           "America/Creston","Canada/Eastern","Canada/Central","Canada/Mountain","Canada/Pacific","Canada/Atlantic",
           "Canada/Newfoundland","Canada/Saskatchewan","Canada/Yukon"],
    "GB": ["Europe/London","GMT","GMT+0","GMT0","GB","Etc/GMT","Etc/GMT+0"],
    "AU": ["Australia/Sydney","Australia/Melbourne","Australia/Brisbane","Australia/Perth","Australia/Adelaide",
           "Australia/Hobart","Australia/Darwin","Australia/Lindeman","Australia/Lord_Howe","Australia/Broken_Hill",
           "Australia/Eucla","Antarctica/Macquarie"],
    "BD": ["Asia/Dhaka","Asia/Thimphu","Asia/Almaty","Asia/Bishkek","Asia/Omsk","Asia/Qyzylorda","Asia/Yekaterinburg","Dhaka"],
    "IN": ["Asia/Kolkata","Asia/Calcutta","Asia/Colombo","Asia/Karachi"],
    "DE": ["Europe/Berlin","Europe/Busingen","CET","Etc/GMT-1"],
    "SG": ["Asia/Singapore","Singapore","Asia/Kuala_Lumpur","Asia/Makassar","Asia/Manila"],
    "MY": ["Asia/Kuala_Lumpur","Asia/Kuching","Asia/Singapore","Singapore","Asia/Makassar"],
    "AE": ["Asia/Dubai","Asia/Muscat","Asia/Qatar","Asia/Riyadh","Asia/Aden","Asia/Kuwait","Asia/Bahrain"],
    "SA": ["Asia/Riyadh","Asia/Qatar","Asia/Bahrain","Asia/Kuwait","Asia/Aden","Asia/Dubai","Asia/Muscat"],
    "FR": ["Europe/Paris","Europe/Monaco","CET","Etc/GMT-1"],
    "NL": ["Europe/Amsterdam","Europe/Berlin","CET","Etc/GMT-1"],
    "JP": ["Asia/Tokyo","Asia/Jayapura","Japan","Asia/Dili","Asia/Palau","Asia/Jayapura"],
    "PK": ["Asia/Karachi","Asia/Kolkata","Asia/Colombo","Pakistan"],
    "NZ": ["Pacific/Auckland","Pacific/Chatham","Antarctica/McMurdo","NZ"],
    "IE": ["Europe/Dublin","Europe/London","GMT","Eire"],
    "SE": ["Europe/Stockholm","Europe/Berlin","CET","Europe/Helsinki","Etc/GMT-1"],
    "CH": ["Europe/Zurich","Europe/Vaduz","CET","Etc/GMT-1"],
    "IT": ["Europe/Rome","Europe/Vatican","Europe/San_Marino","CET","Italy","Etc/GMT-1"],
    "ES": ["Europe/Madrid","Africa/Ceuta","Atlantic/Canary","CET","Europe/Lisbon"],
    "RU": ["Europe/Kaliningrad","Europe/Moscow","Europe/Simferopol","Europe/Kirov","Europe/Volgograd","Europe/Samara",
           "Europe/Saratov","Europe/Ulyanovsk","Asia/Yekaterinburg","Asia/Omsk","Asia/Novosibirsk","Asia/Barnaul",
           "Asia/Tomsk","Asia/Novokuznetsk","Asia/Krasnoyarsk","Asia/Irkutsk","Asia/Chita","Asia/Yakutsk","Asia/Khandyga",
           "Asia/Vladivostok","Asia/Ust-Nera","Asia/Magadan","Asia/Sakhalin","Asia/Srednekolymsk","Asia/Ust-Nera",
           "Asia/Anadyr","Asia/Kamchatka","Asia/Chita"],
    "BR": ["America/Noronha","America/Belem","America/Fortaleza","America/Recife","America/Araguaina","America/Maceio",
           "America/Bahia","America/Sao_Paulo","America/Campo_Grande","America/Cuiaba","America/Santarem","America/Porto_Velho",
           "America/Boa_Vista","America/Manaus","America/Eirunepe","America/Rio_Branco"],
    "MX": ["America/Mexico_City","America/Cancun","America/Merida","America/Monterrey","America/Matamoros","America/Mazatlan",
           "America/Chihuahua","America/Ojinaga","America/Hermosillo","America/Tijuana","America/Bahia_Banderas"],
    "ZA": ["Africa/Johannesburg","Africa/Maseru","Africa/Mbabane","Africa/Maputo","Africa/Gaborone","Africa/Harare"],
    "KR": ["Asia/Seoul","Asia/Pyongyang","ROK","Korea"],
    "CN": ["Asia/Shanghai","Asia/Urumqi","Asia/Hong_Kong","Asia/Macau","Asia/Taipei","PRC","Asia/Chongqing","Asia/Harbin"],
    "ID": ["Asia/Jakarta","Asia/Pontianak","Asia/Makassar","Asia/Jayapura"],
    "PH": ["Asia/Manila","Asia/Brunei","Asia/Makassar"],
    "VN": ["Asia/Ho_Chi_Minh","Asia/Bangkok","Asia/Saigon","Asia/Phnom_Penh","Asia/Vientiane"],
    "TH": ["Asia/Bangkok","Asia/Ho_Chi_Minh","Asia/Phnom_Penh","Asia/Vientiane","Asia/Brunei","Asia/Saigon","Asia/Jakarta","Asia/Krasnoyarsk"],
    "TR": ["Europe/Istanbul","Asia/Bahrain","Asia/Baghdad","Asia/Riyadh","Europe/Moscow","Etc/GMT-3"],
    "EG": ["Africa/Cairo","Asia/Jerusalem","Asia/Gaza","Asia/Hebron","EET","Africa/Tripoli"],
    "NG": ["Africa/Lagos","Africa/Porto-Novo","Africa/Niamey","Africa/Luanda","Africa/Libreville","Africa/Douala","WAT"],
    "AR": ["America/Argentina/Buenos_Aires","America/Argentina/Cordoba","America/Argentina/Salta","America/Argentina/Jujuy",
           "America/Argentina/Tucuman","America/Argentina/Catamarca","America/Argentina/La_Rioja","America/Argentina/San_Juan",
           "America/Argentina/Mendoza","America/Argentina/San_Luis","America/Argentina/Rio_Gallegos","America/Argentina/Ushuaia"],
    "CL": ["America/Santiago","America/Punta_Arenas","Pacific/Easter","Chile/Continental","Chile/EasterIsland"],
    "CO": ["America/Bogota","America/Lima","America/Guayaquil","America/Rio_Branco","America/Eirunepe","America/Cayenne"],
    "PE": ["America/Lima","America/Bogota","America/Guayaquil","America/Rio_Branco","America/Eirunepe","America/Cayenne"],
    "LK": ["Asia/Colombo","Asia/Kolkata","Asia/Calcutta"],
    "NP": ["Asia/Kathmandu","Asia/Calcutta","Asia/Kolkata","Asia/Dhaka"],
    "BN": ["Asia/Brunei","Asia/Makassar","Asia/Kuching","Asia/Manila"],
    "HK": ["Asia/Hong_Kong","Asia/Shanghai","Asia/Macau","Asia/Taipei","Hongkong"],
    "TW": ["Asia/Taipei","Asia/Shanghai","Asia/Hong_Kong","Asia/Macau","ROC"],
    "IL": ["Asia/Jerusalem","Asia/Gaza","Asia/Hebron","Asia/Amman","Asia/Beirut","Asia/Damascus","Asia/Tel_Aviv","Israel"],
    "PT": ["Europe/Lisbon","Atlantic/Madeira","Atlantic/Azores","Portugal","WET"],
    "AT": ["Europe/Vienna","Europe/Berlin","CET","Etc/GMT-1"],
    "BE": ["Europe/Brussels","Europe/Amsterdam","Europe/Berlin","CET","Etc/GMT-1"],
    "DK": ["Europe/Copenhagen","Europe/Berlin","CET","Etc/GMT-1"],
    "FI": ["Europe/Helsinki","Europe/Berlin","CET","Etc/GMT-2","Europe/Tallinn"],
    "NO": ["Europe/Oslo","Europe/Berlin","CET","Etc/GMT-1"],
    "PL": ["Europe/Warsaw","Europe/Berlin","CET","Poland","Etc/GMT-1"],
    "CZ": ["Europe/Prague","Europe/Berlin","CET","Etc/GMT-1"],
    "GR": ["Europe/Athens","Europe/Bucharest","Europe/Helsinki","EET","Etc/GMT-2"],
    "HU": ["Europe/Budapest","Europe/Belgrade","CET","Etc/GMT-1"],
    "RO": ["Europe/Bucharest","Europe/Athens","Europe/Helsinki","EET","Etc/GMT-2"],
    "BG": ["Europe/Sofia","Europe/Athens","EET","Etc/GMT-2"],
    "HR": ["Europe/Zagreb","Europe/Belgrade","CET","Etc/GMT-1"],
    "SK": ["Europe/Bratislava","Europe/Prague","Europe/Berlin","CET","Etc/GMT-1"],
    "SI": ["Europe/Ljubljana","Europe/Belgrade","Europe/Zagreb","CET","Etc/GMT-1"],
    "EE": ["Europe/Tallinn","Europe/Helsinki","Europe/Riga","EET","Etc/GMT-2"],
    "LV": ["Europe/Riga","Europe/Tallinn","Europe/Helsinki","EET","Etc/GMT-2"],
    "LT": ["Europe/Vilnius","Europe/Riga","Europe/Tallinn","EET","Etc/GMT-2"],
    "UA": ["Europe/Kyiv","Europe/Kiev","Europe/Minsk","Europe/Helsinki","EET","Etc/GMT-2"],
    "BY": ["Europe/Minsk","Europe/Moscow","Europe/Kyiv","MSK","Etc/GMT-3"],
    "KZ": ["Asia/Almaty","Asia/Qyzylorda","Asia/Aqtobe","Asia/Aqtau","Asia/Atyrau","Asia/Oral","Asia/Oral","Asia/Qyzylorda"],
    "UZ": ["Asia/Tashkent","Asia/Samarkand","Asia/Dushanbe","Asia/Bishkek","Asia/Almaty","Asia/Yekaterinburg"],
    "QA": ["Asia/Qatar","Asia/Bahrain","Asia/Riyadh","Asia/Kuwait","Asia/Aden","Asia/Dubai","Asia/Muscat"],
    "KW": ["Asia/Kuwait","Asia/Riyadh","Asia/Qatar","Asia/Bahrain","Asia/Aden","Asia/Dubai","Asia/Muscat"],
    "BH": ["Asia/Bahrain","Asia/Qatar","Asia/Riyadh","Asia/Kuwait","Asia/Aden","Asia/Dubai","Asia/Muscat"],
    "OM": ["Asia/Muscat","Asia/Dubai","Asia/Qatar","Asia/Riyadh","Asia/Kuwait","Asia/Bahrain","Asia/Aden"],
    "JO": ["Asia/Amman","Asia/Jerusalem","Asia/Gaza","Asia/Hebron","Asia/Beirut","Asia/Damascus"],
    "LB": ["Asia/Beirut","Asia/Jerusalem","Asia/Gaza","Asia/Hebron","Asia/Amman","Asia/Damascus"],
    "IQ": ["Asia/Baghdad","Asia/Riyadh","Asia/Kuwait","Asia/Tehran","Asia/Bahrain"],
    "IR": ["Asia/Tehran","Asia/Qazvin","Asia/Tehran","Iran"],
    "AF": ["Asia/Kabul","Asia/Karachi","Asia/Tashkent","Asia/Dushanbe","Asia/Tehran","Asia/Ashgabat"],
    "MM": ["Asia/Yangon","Asia/Rangoon","Asia/Dhaka","Asia/Bangkok","Asia/Ho_Chi_Minh","Asia/Kolkata","Indian/Christmas"],
    "KH": ["Asia/Phnom_Penh","Asia/Bangkok","Asia/Ho_Chi_Minh","Asia/Vientiane","Asia/Saigon"],
    "LA": ["Asia/Vientiane","Asia/Bangkok","Asia/Ho_Chi_Minh","Asia/Phnom_Penh","Asia/Saigon"],
    "MO": ["Asia/Macau","Asia/Hong_Kong","Asia/Shanghai","Asia/Taipei"],
}
_ipcache = {}

def client_ip():
    h = request.headers
    return (h.get("CF-Connecting-IP") or h.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or "").strip()

def get_country():
    code = (request.headers.get("CF-IPCountry") or "").strip().upper()
    if len(code) == 2 and code not in ("XX", "T1"): return code, CNAME.get(code, code)
    ip = client_ip()
    if not ip: return "", ""
    c = _ipcache.get(ip)
    if c and time.time() - c[2] < 1800: return c[0], c[1]
    code = name = ""
    try:
        import urllib.request
        with urllib.request.urlopen(f"https://ipwho.is/{ip}?fields=success,country,country_code", timeout=2.5) as r:
            j = json.loads(r.read().decode())
            if j.get("success", True): code = (j.get("country_code") or "").upper(); name = j.get("country") or ""
    except Exception: pass
    _ipcache[ip] = (code, name, time.time())
    return code, name

def country_ok(allowed, code, name):
    """allowed may be a single country code/name or comma-separated list.
    Returns True if no restriction is set OR the user's country matches any allowed country."""
    a_list = parse_allowed(allowed)
    if not a_list: return True  # nothing required -> allow everyone
    if not code and not name: return True  # could not detect -> don't block (legacy behavior)
    user_codes = set()
    if code: user_codes.add(code.lower())
    if name: user_codes.add(ALIAS.get(name.lower(), name.lower()))
    return any(c.lower() in user_codes for c in a_list)

def tz_ok(allowed, user_tz):
    """user_tz = e.g. 'Asia/Dhaka'. Returns True if it matches any allowed country's tz list.
    If no restriction set, or no tz provided, or no tz-data for any allowed country, returns True
    (so we never block harder than the IP check when we don't have tz data)."""
    a_list = parse_allowed(allowed)
    if not a_list: return True  # nothing required
    if not user_tz: return True  # couldn't read phone tz -> don't block (legacy / old client)
    user_tz = str(user_tz).strip()
    has_any_tz = False
    for c in a_list:
        tzs = COUNTRY_TZ.get(c.upper(), [])
        if tzs:
            has_any_tz = True
            if user_tz in tzs: return True
    # If we don't have tz data for any allowed country, don't block on tz
    if not has_any_tz: return True
    return False

def tz_ok_for_any(allowed, user_tz):
    """same as tz_ok but returns True also when no tz data — used internally for clarity."""
    return tz_ok(allowed, user_tz)

def parse_allowed(allowed):
    """returns list of upper-case 2-letter codes parsed from comma/semicolon/space separated input.
    Accepts both codes (CA) and country names (Canada) and common aliases (USA, UK)."""
    if not allowed: return []
    out = []
    seen = set()
    raw = str(allowed).replace(";", ",").replace("/", ",").replace(" ", ",")
    for x in raw.split(","):
        x = x.strip()
        if not x: continue
        xl = x.lower()
        code = ALIAS.get(xl, xl)
        if len(code) == 2:
            code = code.upper()
            if code not in seen:
                seen.add(code); out.append(code)
    return out

def allowed_display(allowed):
    """returns list of dicts {code, name, flag} for the allowed countries (for the popup)."""
    out = []
    for c in parse_allowed(allowed):
        out.append({"code": c, "name": CNAME.get(c, c), "flag": FLAG.get(c, "🏳️")})
    return out

def country_notice(s, name, code):
    return str(s.get("country_notice", "")).replace("{country}", s.get("vpn_country", "")).replace("{current}", name or code or "Unknown")

def loc_block_response(s, code, name, ip, phone_tz):
    """Build the JSON response for /api/ad/start when the ad is blocked because of
    country / timezone mismatch. Includes everything the frontend needs to render
    the popup exactly like screenshot 2."""
    allowed = s.get("vpn_country", "")
    allowed_list = allowed_display(allowed)
    # Primary "selected server" = first allowed country (for the headline)
    primary = allowed_list[0] if allowed_list else {"code": "", "name": "—", "flag": "🏳️"}
    c_ok = country_ok(allowed, code, name)
    t_ok = tz_ok(allowed, phone_tz)
    # Headline message
    if not c_ok and not t_ok:
        msg = "আপনার IP লোকেশন এবং ফোনের টাইম জোন নির্বাচিত সার্ভারের সাথে মিলছে না।"
        hint = "VPN/Proxy অন করুন এবং ফোনের Settings → টাইম জোন পরিবর্তন করুন।"
    elif not c_ok:
        msg = "আপনার IP লোকেশন নির্বাচিত সার্ভারের সাথে মিলছে না।"
        hint = "VPN/Proxy অন করুন এবং অনুমোদিত দেশ সিলেক্ট করুন।"
    elif not t_ok:
        msg = "আপনার ফোনের টাইম জোন নির্বাচিত সার্ভারের সাথে মিলছে না।"
        hint = "ফোনের Settings → টাইম জোন পরিবর্তন করুন। (VPN অন থাকলেও টাইম জোন ঠিক করতে হবে)"
    else:
        msg = "লোকেশন যাচাই ব্যর্থ হয়েছে।"
        hint = ""
    return jsonify(error="country", notice=msg, hint=hint,
                   selected_server=primary,
                   allowed_countries=allowed_list,
                   current_country={"code": code, "name": name or (CNAME.get(code, "") if code else ""), "flag": FLAG.get(code, "🏳️") if code else "🏳️"},
                   ip=ip, phone_tz=phone_tz, country_ok=c_ok, tz_ok=t_ok)

# ---------- public / user API ----------
@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    with _lock:
        d = load(); cur = settings_of(d)
        if request.method == 'POST':
            if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
            try:
                s = request.get_json(force=True) or {}
                for k in ("reward_watch", "reward_auto"):
                    if k in s: cur[k] = max(0.0, float(s[k]))
                for k in cur["min"]:
                    if k in s.get("min", {}): cur["min"][k] = max(0.0, float(s["min"][k]))
                if "vpn_country" in s: cur["vpn_country"] = str(s["vpn_country"])[:200]
                if "notice" in s: cur["notice"] = str(s["notice"])[:300]
                if "country_notice" in s: cur["country_notice"] = str(s["country_notice"])[:300]
                if "bot_guidelines" in s: cur["bot_guidelines"] = str(s["bot_guidelines"])[:2000]
                if "home_notice" in s: cur["home_notice"] = str(s["home_notice"])[:500]
                if "usdt_rate" in s: cur["usdt_rate"] = max(0.0, float(s["usdt_rate"]))
                if "payment_methods" in s and isinstance(s["payment_methods"], dict):
                    for mk in ("bkash","nagad","rocket","binance","recharge"):
                        if mk in s["payment_methods"]:
                            cur["payment_methods"][mk] = bool(s["payment_methods"][mk])
                if "ref_bonus" in s: cur["ref_bonus"] = min(100.0, max(0.0, float(s["ref_bonus"])))
                for k in ("limit_watch", "limit_auto"):
                    if k in s: cur[k] = max(0, int(float(s[k])))
            except Exception: return jsonify(error="bad data"), 400
            save(d)
        return jsonify(cur)

@app.route('/api/register', methods=['POST'])
def api_register():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); ensure_user(d, u); save(d)
    return jsonify(ok=True)

@app.route('/api/me', methods=['POST'])
def api_me():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    b = request.get_json(silent=True) or {}
    phone_tz = str(b.get("phone_tz") or "").strip()
    code, name = get_country()
    with _lock:
        d = load(); s = settings_of(d); uid = str(u["id"])
        fresh = uid not in d["users"] or "bal" not in d["users"][uid]
        rec = ensure_user(d, u); migrated = False
        rec["last_seen"] = int(time.time()); rec["country"] = code; rec["country_name"] = name
        if phone_tz: rec["phone_tz"] = phone_tz[:60]
        lg = b.get("legacy")
        if fresh and isinstance(lg, dict):
            try:
                bl = rec["bal"]
                bl["main"] = min(10000000.0, max(0.0, float(lg.get("main", 0))))
                bl["pending"] = min(10000000.0, max(0.0, float(lg.get("pending", 0))))
                bl["today_ads"] = min(100000, max(0, int(float(lg.get("today_ads", 0)))))
                bl["total_ads"] = min(10000000, max(0, int(float(lg.get("total_ads", 0)))))
                migrated = True
            except Exception: pass
        save(d)
        if rec.get("banned"): return jsonify(ok=True, banned=True)
        allowed = s.get("vpn_country", "")
        c_ok = country_ok(allowed, code, name)
        t_ok = tz_ok(allowed, phone_tz)
        loc_ok = c_ok and t_ok
        return jsonify(ok=True, banned=False, migrated=migrated, state=state(rec), settings=s,
                       country={"code": code, "name": name, "ok": loc_ok, "country_ok": c_ok, "tz_ok": t_ok,
                                "phone_tz": phone_tz, "allowed": allowed_display(allowed), "ip": client_ip()},
                       refs=ref_stats(d, uid), withdraws=user_withdraws(d, uid), is_admin=is_admin(u))

@app.route('/api/ad/start', methods=['POST'])
def api_ad_start():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    body = request.get_json(silent=True) or {}
    t = body.get("type")
    phone_tz = str(body.get("phone_tz") or "").strip()
    if t not in ("watch", "auto"): return jsonify(error="bad data"), 400
    with _lock:
        d = load(); s = settings_of(d); rec = ensure_user(d, u)
        if rec.get("banned"): return jsonify(error="banned")
    code, name = get_country()
    ip = client_ip()
    with _lock:
        d = load(); s = settings_of(d); rec = ensure_user(d, u)
        allowed = s.get("vpn_country", "")
        c_ok = country_ok(allowed, code, name)
        t_ok = tz_ok(allowed, phone_tz)
        # Block if either IP location OR phone timezone doesn't match the allowed country.
        # This way: even if VPN makes the IP look right, the user's phone timezone must also match.
        if not c_ok or not t_ok:
            return loc_block_response(s, code, name, ip, phone_tz)
        roll(rec); b = rec["bal"]
        lim = s["limit_watch"] if t == "watch" else s["limit_auto"]
        if b[t + "_today"] >= lim: return jsonify(error="limit", type=t, limit=lim)
        rec["ad"] = {"type": t, "t": time.time()}
        if phone_tz: rec["phone_tz"] = phone_tz[:60]
        save(d)
    return jsonify(ok=True)

@app.route('/api/ad/claim', methods=['POST'])
def api_ad_claim():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); s = settings_of(d); rec = ensure_user(d, u)
        if rec.get("banned"): return jsonify(error="banned")
        ad = rec.get("ad")
        if not ad: return jsonify(error="noad")
        wait = AD_MIN_SECONDS - (time.time() - ad["t"])
        if wait > 0: return jsonify(error="early", wait=round(wait, 1))
        roll(rec); b = rec["bal"]; t = ad["type"]
        lim = s["limit_watch"] if t == "watch" else s["limit_auto"]
        rec.pop("ad", None)
        if b[t + "_today"] >= lim:
            save(d); return jsonify(error="limit", type=t, limit=lim)
        reward = float(s["reward_watch"] if t == "watch" else s["reward_auto"])
        b["pending"] = round(b["pending"] + reward, 4)
        b["today_ads"] += 1; b["total_ads"] += 1; b[t + "_today"] += 1
        pct = float(s.get("ref_bonus", 0) or 0); rid = rec.get("ref")
        if rid and pct > 0:
            rr = d["users"].get(str(rid))
            if rr and not rr.get("banned") and "bal" in rr:
                bonus = round(reward * pct / 100.0, 4)
                rr["bal"]["main"] = round(rr["bal"]["main"] + bonus, 4); rr["ref_earned"] = round(rr.get("ref_earned", 0) + bonus, 4)
        save(d)
        return jsonify(ok=True, state=state(rec), reward=reward)

@app.route('/api/confirm', methods=['POST'])
def api_confirm():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); rec = ensure_user(d, u)
        if rec.get("banned"): return jsonify(error="banned")
        roll(rec); b = rec["bal"]
        if b["pending"] <= 0: return jsonify(error="nopending")
        if b["total_ads"] < 1: return jsonify(error="noads")
        b["main"] = round(b["main"] + b["pending"], 4); b["pending"] = 0.0
        save(d)
        return jsonify(ok=True, state=state(rec))

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    try:
        b = request.get_json(force=True) or {}
        method = str(b.get("method", ""))[:20]; number = str(b.get("number", "")).strip()[:30]; amount = round(float(b.get("amount", 0)), 2)
    except Exception: return jsonify(error="bad data"), 400
    with _lock:
        d = load(); s = settings_of(d); rec = ensure_user(d, u)
        if rec.get("banned"): return jsonify(error="banned")
        if method not in s["min"] or not number or amount <= 0: return jsonify(error="bad data")
        roll(rec); bl = rec["bal"]
        if amount < s["min"][method]: return jsonify(error="min", min=s["min"][method], method=method)
        if amount > bl["main"] + 1e-9: return jsonify(error="balance", main=round(bl["main"], 2))
        bl["main"] = round(bl["main"] - amount, 4)
        w = {"id": int(time.time() * 1000), "uid": u["id"], "name": uname(u), "username": u.get("username", ""), "method": method, "number": number,
             "amount": amount, "bal": round(bl["main"], 2), "status": "Pending", "date": int(time.time())}
        d["withdraws"].insert(0, w); save(d)
        return jsonify(ok=True, state=state(rec), withdraws=user_withdraws(d, u["id"]))

# ---------- admin API ----------
@app.route('/api/admin/data')
def api_admin_data():
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); users = []
        for r in d["users"].values():
            bl = r.get("bal") or {}
            users.append({"id": r["id"], "name": r.get("name", ""), "username": r.get("username", ""), "joined": r.get("joined", 0),
                          "country": r.get("country_name") or r.get("country", ""), "banned": bool(r.get("banned")),
                          "is_admin": int(r["id"]) == ADMIN_ID, "main": round(bl.get("main", 0), 2), "pending": round(bl.get("pending", 0), 2)})
        users.sort(key=lambda x: -x["joined"])
        return jsonify(users=users, withdraws=d["withdraws"])

@app.route('/api/admin/withdraw_status', methods=['POST'])
def api_admin_wstatus():
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    b = request.get_json(force=True) or {}
    if b.get("status") not in ("Approved", "Rejected"): return jsonify(error="bad status"), 400
    with _lock:
        d = load()
        for w in d["withdraws"]:
            if w["id"] == b.get("id"):
                if w["status"] != "Pending": return jsonify(error="locked")  # once approved/rejected it can never change again
                w["status"] = b["status"]  # no refund on reject
        save(d)
    return jsonify(ok=True)

@app.route('/api/admin/user_ban', methods=['POST'])
def api_admin_ban():
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    b = request.get_json(force=True) or {}
    try: uid = int(b.get("id"))
    except Exception: return jsonify(error="bad data"), 400
    if uid == ADMIN_ID: return jsonify(error="admin cannot be banned")
    with _lock:
        d = load(); rec = d["users"].get(str(uid))
        if not rec: return jsonify(error="no user")
        rec["banned"] = bool(b.get("banned")); rec.pop("ad", None); save(d)
    return jsonify(ok=True)

@app.route('/api/admin/user_balance', methods=['POST'])
def api_admin_balance():
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    b = request.get_json(force=True) or {}
    try: uid = str(int(b.get("id"))); main = max(0.0, float(b.get("main"))); pend = max(0.0, float(b.get("pending")))
    except Exception: return jsonify(error="bad data"), 400
    with _lock:
        d = load(); rec = d["users"].get(uid)
        if not rec: return jsonify(error="no user")
        if "bal" not in rec: rec["bal"] = new_bal()
        rec["bal"]["main"] = round(main, 4); rec["bal"]["pending"] = round(pend, 4); save(d)
    return jsonify(ok=True)

@app.route('/api/admin/clear_withdraws', methods=['POST'])
def api_admin_clear_withdraws():
    """Clears ALL withdraw history (does not touch user balances, refs, or settings)."""
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    with _lock:
        d = load()
        n = len(d.get("withdraws", []))
        d["withdraws"] = []
        save(d)
    return jsonify(ok=True, cleared=n)

@app.route('/api/admin/reset_ads', methods=['POST'])
def api_admin_reset_ads():
    """Resets every user's ad counters (today_ads, total_ads, watch_today, auto_today) to 0."""
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); cnt = 0
        for rec in d["users"].values():
            if "bal" in rec:
                b = rec["bal"]
                b["today_ads"] = 0; b["total_ads"] = 0
                b["watch_today"] = 0; b["auto_today"] = 0
                b["day"] = today_key()
                cnt += 1
            rec.pop("ad", None)
        save(d)
    return jsonify(ok=True, users_reset=cnt)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
