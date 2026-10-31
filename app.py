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
DEFAULTS = {"settings": {"reward_watch": 0.5, "reward_auto": 0.10, "limit_watch": 100, "limit_auto": 100,
                         "notice": "📢 VPN diye kaj korbe",
                         "country_notice": "⚠️ {country} VPN/Proxy on korun, tarpor ad dekhun. Apnar current country: {current}",
                         "ref_bonus": 10,
                         "min": {"bkash": 0, "nagad": 0, "rocket": 0, "binance": 0, "recharge": 0}, "vpn_country": ""},
            "users": {}, "withdraws": [], "refs": {}, "legacy_done": False}

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
            d["settings"] = md.get("settings", {}); d["refs"] = md.get("refs", {}); d["legacy_done"] = bool(md.get("legacy_done"))
            d["users"] = {x.id: x.to_dict() for x in _db.collection("atm_users").stream()}
            d["withdraws"] = sorted([x.to_dict() for x in _db.collection("atm_withdraws").stream()], key=lambda w: -int(w.get("id", 0)))
            if not d["legacy_done"]:
                # one-time: bring over the OLD data kept in Firestore document  atm/main_data  (the old docs are never deleted)
                ld = _db.collection("atm").document("main_data").get()
                if ld.exists:
                    old = ld.to_dict() or {}
                    for uid, rec in (old.get("users") or {}).items():
                        if isinstance(rec, dict): d["users"].setdefault(str(uid), rec)
                    have = {int(w.get("id", 0)) for w in d["withdraws"]}
                    for w in (old.get("withdraws") or []):
                        if not isinstance(w, dict) or int(w.get("id", 0)) in have: continue
                        for k, v in (("id", 0), ("uid", 0), ("name", ""), ("method", ""), ("number", ""), ("amount", 0), ("status", "Pending"), ("date", 0)): w.setdefault(k, v)
                        d["withdraws"].append(w)
                    d["withdraws"].sort(key=lambda w: -int(w.get("id", 0)))
                    os_ = old.get("settings") or {}
                    if os_:
                        cur = d["settings"]; newer = {k: v for k, v in cur.items() if k != "min" and v != DEFAULTS["settings"].get(k)}
                        newer_min = {k: v for k, v in (cur.get("min") or {}).items() if v != DEFAULTS["settings"]["min"].get(k)}
                        d["settings"] = dict(os_); d["settings"].update(newer)
                        d["settings"].setdefault("min", {}); d["settings"]["min"].update(newer_min)
                else:
                    try:
                        with open(DATA_FILE, encoding='utf-8') as f: old = json.load(f)
                        for uid, rec in (old.get("users") or {}).items(): d["users"].setdefault(str(uid), rec)
                    except Exception: pass
                d["legacy_done"] = True
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
        meta = {"settings": d["settings"], "refs": d["refs"], "legacy_done": bool(d.get("legacy_done"))}; mh = _js(meta)
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
    return [{"id": w.get("id", 0), "method": w.get("method", ""), "number": w.get("number", ""), "amount": w.get("amount", 0), "status": w.get("status", "Pending"), "date": w.get("date", 0)}
            for w in d["withdraws"] if str(w.get("uid")) == str(uid)][:50]

# ---------- country check ----------
CNAME = {"US": "United States", "AU": "Australia", "BD": "Bangladesh", "IN": "India", "GB": "United Kingdom", "CA": "Canada", "DE": "Germany",
         "SG": "Singapore", "MY": "Malaysia", "AE": "United Arab Emirates", "SA": "Saudi Arabia", "FR": "France", "NL": "Netherlands",
         "JP": "Japan", "PK": "Pakistan", "NZ": "New Zealand", "IE": "Ireland", "SE": "Sweden", "CH": "Switzerland", "IT": "Italy", "ES": "Spain"}
ALIAS = {v.lower(): k.lower() for k, v in CNAME.items()}
ALIAS.update({"usa": "us", "america": "us", "united states of america": "us", "uk": "gb", "england": "gb", "britain": "gb", "uae": "ae"})
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
    a = (allowed or "").strip().lower()
    if not a: return True
    if not code and not name: return True  # could not detect -> do not block
    a = ALIAS.get(a, a)
    return a in {code.lower(), name.lower(), ALIAS.get(name.lower(), "")}

def country_notice(s, name, code):
    return str(s.get("country_notice", "")).replace("{country}", s.get("vpn_country", "")).replace("{current}", name or code or "Unknown")

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
                if "vpn_country" in s: cur["vpn_country"] = str(s["vpn_country"])[:40]
                if "notice" in s: cur["notice"] = str(s["notice"])[:300]
                if "country_notice" in s: cur["country_notice"] = str(s["country_notice"])[:300]
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
    code, name = get_country()
    with _lock:
        d = load(); s = settings_of(d); uid = str(u["id"])
        fresh = uid not in d["users"] or "bal" not in d["users"][uid]
        rec = ensure_user(d, u); migrated = False
        rec["last_seen"] = int(time.time()); rec["country"] = code; rec["country_name"] = name
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
        return jsonify(ok=True, banned=False, migrated=migrated, state=state(rec), settings=s,
                       country={"code": code, "name": name, "ok": country_ok(s["vpn_country"], code, name)},
                       refs=ref_stats(d, uid), withdraws=user_withdraws(d, uid), is_admin=is_admin(u))

@app.route('/api/ad/start', methods=['POST'])
def api_ad_start():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    t = (request.get_json(silent=True) or {}).get("type")
    if t not in ("watch", "auto"): return jsonify(error="bad data"), 400
    with _lock:
        d = load(); s = settings_of(d); rec = ensure_user(d, u)
        if rec.get("banned"): return jsonify(error="banned")
    code, name = get_country()
    with _lock:
        d = load(); s = settings_of(d); rec = ensure_user(d, u)
        if not country_ok(s["vpn_country"], code, name): return jsonify(error="country", notice=country_notice(s, name, code))
        roll(rec); b = rec["bal"]
        lim = s["limit_watch"] if t == "watch" else s["limit_auto"]
        if b[t + "_today"] >= lim: return jsonify(error="limit", type=t, limit=lim)
        rec["ad"] = {"type": t, "t": time.time()}
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
