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

# =====================================================================
#  TELEGRAM CHAT SIDE  (/start message, admin commands, /stopbot, /startbot, notices)
# =====================================================================
from html import escape as hesc
TG_CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/SmartWorkCommunity")
TG_ADMIN_URL = os.getenv("ADMIN_URL", "https://t.me/noyonfb1020")
BRAND = "AUTO TAKA MACHINE"
_bc_lock = threading.Lock(); _bc_running = False

def fancy(title, body):
    return ("тФПтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФУ\n  ЁЯТО <b>" + title + "</b> ЁЯТ░\nтФЧтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФЫ\n\n" + body +
            "\n\nтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА\nЁЯдЦ <b>" + BRAND + "</b>")

def countries_text(s):
    out = []
    for c in parse_allowed(s.get("vpn_country", "")):
        c = str(c).upper(); out.append(FLAG.get(c, "ЁЯП│я╕П") + " " + CNAME.get(c, c))
    return ", ".join(out)

def min_text(s):
    m = s.get("min") or {}
    vals = []
    for k in ("bkash", "nagad", "rocket", "recharge"):
        try: v = float(m.get(k, 0) or 0)
        except Exception: v = 0
        if v > 0: vals.append(v)
    return ("%.2f" % min(vals)) if vals else ""

def welcome_html(name, s):
    lines = ["ЁЯТО <b>" + BRAND + "</b> ЁЯТ░", "", "ЁЯСЛ Hello <b>" + hesc(name) + "</b>", "",
             "тЬЕ VPN ржмрзНржпржмрж╣рж╛рж░ ржХрж░рзЗ ржХрж╛ржЬ ржХрж░рждрзЗ рж╣ржмрзЗ тАФ ЁЯМН ржХрж╛ржирзНржЯрзНрж░рж┐ рж╣ржмрзЗ ржЕрзНржпрж╛ржбржорж┐ржирзЗрж░ рж░рзБрж▓рж╕ ржЕржирзБржпрж╛ржпрж╝рзА ЁЯдЭ",
             "тЬЕ ржорж┐ржирж┐ржорж╛ржо Withdraw: <b>100.00 TK</b> ЁЯТ╕",
             "", "ЁЯУв <b>Bot Channel</b>-ржП ржЕржмрж╢рзНржпржЗ ржЬржпрж╝рзЗржи ржерж╛ржХрзБржи!", "ржЖржкржбрзЗржЯ, ржкрзЗржорзЗржирзНржЯ ржирзЛржЯрж┐рж╢ ржЖрж░ ржкрзНрж░рзБржл рж╕ржмрж╛рж░ ржЖржЧрзЗ ржУржЦрж╛ржирзЗржЗ ржкрж╛ржмрзЗржи тЬи",
             "", "ЁЯСЗ ржирж┐ржЪрзЗрж░ ржмрж╛ржЯржирзЗ ржХрзНрж▓рж┐ржХ ржХрж░рзЗ ржмржЯ ржУржкрзЗржи ржХрж░рзБржи:"]
    return "\n".join(lines)

def maint_html():
    return fancy("BOT UPDATE ржЪрж▓ржЫрзЗ ЁЯЫая╕П",
                 "тЪая╕П ржмржЯ ржЖржкржбрзЗржЯрзЗрж░ ржХрж╛ржЬ ржЪрж▓ржЫрзЗ, рждрж╛ржЗ ржХрж┐ржЫрзБржХрзНрж╖ржгрзЗрж░ ржЬржирзНржп <b>ржмржирзНржз</b> ржЖржЫрзЗред\n\n"
                 "тП│ ржПржХржЯрзБ ржкрж░рзЗ ржЖржмрж╛рж░ ржЪрзЗрж╖рзНржЯрж╛ ржХрж░рзБржиред\nЁЯУв ржирждрзБржи ржЖржкржбрзЗржЯ ржкрзЗрждрзЗ Channel ржП ржерж╛ржХрзБржиред\n\nЁЯЩП ржзржирзНржпржмрж╛ржж")

def permoff_html():
    return ("тФПтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФУ\n  ЁЯЫС <b>ржХрж╛ржЬ ржПржЦржи ржмржирзНржз ржЖржЫрзЗ</b> ЁЯЫС\nтФЧтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФЫ\n\n"
            "ЁЯШФ <b>ржжрзБржГржЦрж┐ржд!</b> ржПржЦржи ржХрж╛ржЬ ржмржирзНржз ржЖржЫрзЗред\n\n"
            "тЬЕ ржЕрзНржпрж╛ржбржорж┐ржи ржХрж╛ржЬ ржЪрж╛рж▓рзБ ржХрж░рж▓рзЗ рждржЦржи ржЖржмрж╛рж░ ржХрж╛ржЬ ржХрж░рждрзЗ ржкрж╛рж░ржмрзЗржиред\n\n"
            "ЁЯЩП ржкрзБржирж░рж╛ржпрж╝ ржзржирзНржпржмрж╛ржж ЁЯТЭ\n\nтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА\nЁЯдЦ <b>" + BRAND + "</b>")

def live_html():
    return fancy("ЁЯЪА BOT IS NOW LIVE", "ЁЯЯв <b>ржмржЯ ржПржЦржи рж╕ржорзНржкрзВрж░рзНржг ржЪрж╛рж▓рзБ!</b>\n\nЁЯОЙ рж╕ржмрж╛ржЗ ржПржЦржи ржЖржмрж╛рж░ ржХрж╛ржЬ рж╢рзБрж░рзБ ржХрж░рждрзЗ ржкрж╛рж░ржмрзЗржиред\nЁЯТО " + BRAND + "-ржП рж╕рзНржмрж╛ржЧрждржо!\n\nЁЯСЗ ржмржЯ start ржХрж░рзЗ ржХрж╛ржЬ рж╢рзБрж░рзБ ржХрж░рзБржиред")

def _mk(rows):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    out = []
    for row in rows:
        r = []
        for label, v in row:
            if isinstance(v, dict) and "web_app" in v: r.append(InlineKeyboardButton(label, web_app=WebAppInfo(url=v["web_app"])))
            elif isinstance(v, dict) and "cb" in v: r.append(InlineKeyboardButton(label, callback_data=v["cb"]))
            else: r.append(InlineKeyboardButton(label, url=v))
        out.append(r)
    return InlineKeyboardMarkup(out)

def home_markup():
    return _mk([[("ЁЯЪА Open Auto Taka Machine ЁЯТ░", {"web_app": WEBAPP_URL})],
                [("ЁЯУв Official Channel", TG_CHANNEL_URL), ("ЁЯСд Admin ID", TG_ADMIN_URL)]])

# ---- fixed notices the admin can send to everybody (edit the texts here if you want) ----
def notice_msg(key, s):
    if key == "payment":
        return fancy("PAYMENT NOTICE", "ЁЯТ│ <b>Payment Update:</b> ржкрзЗржорзЗржирзНржЯ рж╕ржВржХрзНрж░рж╛ржирзНржд ржЖржкржбрзЗржЯрзЗрж░ ржЬржирзНржп ржЕржкрзЗржХрзНрж╖рж╛ ржХрж░рзБржи ржПржмржВ рж╕ржарж┐ржХ рждржерзНржп ржЕржирзБрж╕рж░ржг ржХрж░рзБржиред")
    if key == "payrunning":
        return fancy("ЁЯФД PAYMENT RUNNING", "ЁЯУг ржпрж╛рж░рж╛ ржПржЦржирзЛ Withdraw Request ржжрзЗржиржирж┐, рждрж╛ржбрж╝рж╛рждрж╛ржбрж╝рж┐ ржжрж┐ржпрж╝рзЗ ржжрж┐ржиред\n\nЁЯТ░ <b>All Payment Running</b>")
    if key == "allpayment":
        return fancy("ALL PAYMENT COMPLETE тЬЕ",
                     "ЁЯУг ржПржЗ ржкрж░рзНржпржирзНржд ржпрждржЧрзБрж▓рзЛ рж░рж┐ржХрзЛржпрж╝рзЗрж╕рзНржЯ ржжрж┐ржпрж╝рзЗржЫрж┐рж▓рзЗржи, рж╕ржХрж▓ ржкрзЗржорзЗржирзНржЯ <b>ржХрзНрж▓рж┐ржпрж╝рж╛рж░</b> тЬЕ\n\n"
                     "ЁЯСН рж╕ржмрж╛ржЗ ржирж┐ржЬрзЗрж░ ржПржХрж╛ржЙржирзНржЯ ржЪрзЗржХ ржХрж░рзБржи, ржкрзЗржорзЗржирзНржЯ ржЪрж▓рзЗ ржЧрзЗржЫрзЗ ЁЯФФ\n\n"
                     "тЮбя╕П ржпрж╛рж░рж╛ ржПржЦржирзЛ Withdraw ржжрзЗржиржирж┐, ржжрж┐ржпрж╝рзЗ ржжрж┐ржиред ржПржкрзНрж░рзБржн ржХрж░рзЗ ржирзЗржУржпрж╝рж╛ рж╣ржмрзЗ тЬФя╕П\n\nЁЯЩП Thanks for your support ЁЯТЭ")
    if key == "hello":
        return fancy("ЁЯСЛ Hello Everyone", "тЬи <i>Hello everyone kaj koren sobai</i> ЁЯСЛ")
    if key == "bednotice":
        return maint_html()
    if key == "newstart":
        return "ЁЯдЦ <b>Bot updated ржХрж░рж╛ рж╣ржпрж╝рзЗржЫрзЗ</b>"
    if key == "autorate":
        return fancy("тЪб AUTO ADS RATE", "тЪб ржкрзНрж░рждрж┐ржЯрж╛ <b>Auto Ad</b> ржП ржкрж╛ржмрзЗржи <b>" + str(s.get("reward_auto")) + " TK</b>\n"
                     "ЁЯУК ржжрзИржирж┐ржХ рж▓рж┐ржорж┐ржЯ: <b>" + str(s.get("limit_auto")) + "</b> ржЯрж╛\n\nЁЯТб Auto Loop ржЪрж╛рж▓рзБ ржХрж░рзЗ ржирж┐ржЬрзЗ ржирж┐ржЬрзЗржЗ ad ржжрзЗржЦрзБржиред")
    if key == "watchrate":
        return fancy("тЦ╢я╕П WATCH ADS RATE", "тЦ╢я╕П ржкрзНрж░рждрж┐ржЯрж╛ <b>Watch Ad</b> ржП ржкрж╛ржмрзЗржи <b>" + str(s.get("reward_watch")) + " TK</b> (рж╕рж░рж╛рж╕рж░рж┐ Main Balance ржП)\n"
                     "ЁЯУК ржжрзИржирж┐ржХ рж▓рж┐ржорж┐ржЯ: <b>" + str(s.get("limit_watch")) + "</b> ржЯрж╛")
    return None

NOTICE_LABEL = {"hello": "HELLO", "bednotice": "BED NOTICE", "newstart": "NEW START", "payment": "PAYMENT NOTICE", "payrunning": "PAYMENT RUNNING", "allpayment": "ALL PAYMENT COMPLETE",
                "autorate": "AUTO ADS RATE", "watchrate": "WATCH ADS RATE"}

def start_broadcast(html, button=None, report_to=None, label="Broadcast"):
    """Sends a message to every known user in a background thread (so the webhook answers Telegram instantly)."""
    global _bc_running
    with _bc_lock:
        if _bc_running: return False
        _bc_running = True
    with _lock:
        d = load(); ids = [int(r["id"]) for r in d["users"].values() if r.get("id") and not r.get("banned")]
    def work():
        global _bc_running
        import asyncio
        async def run():
            from telegram import Bot
            from telegram.error import RetryAfter
            ok = fail = 0
            markup = _mk([[button]]) if button else None
            async with Bot(BOT_TOKEN) as bot:
                for cid in ids:
                    for attempt in (1, 2):
                        try:
                            await bot.send_message(cid, html, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
                            ok += 1; break
                        except RetryAfter as e:
                            await asyncio.sleep(float(e.retry_after) + 1)
                            if attempt == 2: fail += 1
                        except Exception:
                            fail += 1; break
                    await asyncio.sleep(0.05)
                if report_to:
                    try: await bot.send_message(report_to, "тЬЕ " + label + ": " + str(ok) + " ржЬржиржХрзЗ ржкрж╛ржарж╛ржирзЛ рж╣ржпрж╝рзЗржЫрзЗ" + ((" тАв ржмрзНржпрж░рзНрже " + str(fail)) if fail else ""))
                    except Exception: pass
        try: asyncio.run(run())
        except Exception:
            import traceback; traceback.print_exc()
        finally:
            with _bc_lock: _bc_running = False
    threading.Thread(target=work, daemon=True).start()
    return True

def _is_admin_update(update):
    u = update.effective_user
    return bool(u) and int(u.id) == ADMIN_ID

def _args_text(update, n=1):
    """text after the command, keeps new lines. n = how many leading words to split off after the command."""
    t = (update.effective_message.text or "")
    parts = t.split(None, n)
    return parts[1:] if len(parts) > 1 else []

async def refresh_menu(bot, user_id):
    """sets the Menu button + command list for this chat (admin = full list, others = only /start)."""
    try:
        from telegram import BotCommand, BotCommandScopeChat, MenuButtonCommands
        cmds = ADMIN_COMMANDS if int(user_id) == ADMIN_ID else [("start", "ЁЯЪА ржмржЯ ржЪрж╛рж▓рзБ ржХрж░рзБржи")]
        await bot.set_my_commands([BotCommand(c, d) for c, d in cmds], scope=BotCommandScopeChat(chat_id=int(user_id)))
        await bot.set_chat_menu_button(chat_id=int(user_id), menu_button=MenuButtonCommands())
    except Exception:
        import traceback; traceback.print_exc()

async def h_id(update, context):
    await update.effective_message.reply_text("ЁЯЖФ Your ID: " + str(update.effective_user.id) + "\nAdmin ID in bot: " + str(ADMIN_ID))

async def h_start(update, context):
    u = update.effective_user; msg = update.effective_message
    try:
        if context.args and context.args[0].isdigit(): register_ref(u.id, context.args[0])
    except Exception: pass
    with _lock:
        d = load(); s = settings_of(d); uid = str(u.id)
        if uid not in d["users"]:   # remember chat-only users so notices can reach them too (balance record is created later when the app opens)
            d["users"][uid] = {"id": u.id, "name": ((u.first_name or "") + " " + (u.last_name or "")).strip(), "username": u.username or "", "joined": int(time.time())}
            save(d)
        perm = bool(s.get("bot_perm_off")); stopped = bool(s.get("bot_stopped")) or perm; html = welcome_html(u.first_name or "User", s)
    admin = int(u.id) == ADMIN_ID
    await refresh_menu(context.bot, u.id)
    if perm and not admin:
        await msg.reply_text(permoff_html(), parse_mode="HTML", reply_markup=_mk([[("ЁЯУв Official Channel", TG_CHANNEL_URL), ("ЁЯСд Admin ID", TG_ADMIN_URL)]]))
        return
    if stopped and not admin:
        await msg.reply_text(maint_html(), parse_mode="HTML", reply_markup=_mk([[("ЁЯУв Official Channel", TG_CHANNEL_URL), ("ЁЯСд Admin ID", TG_ADMIN_URL)]]))
        return
    if stopped and admin: html = "ЁЯЫС <i>ржмржЯ ржПржЦржи ржмржирзНржз ржЖржЫрзЗ (рж╢рзБржзрзБ Admin ржЪрж╛рж▓рж╛рждрзЗ ржкрж╛рж░ржЫрзЗ)</i>\n\n" + html
    await msg.reply_text(html, parse_mode="HTML", reply_markup=home_markup(), disable_web_page_preview=True)

async def h_stopbot(update, context):
    if not _is_admin_update(update): return
    with _lock:
        d = load(); settings_of(d)["bot_stopped"] = True; save(d)
    await update.effective_message.reply_text(
        "ЁЯЫС <b>Bot ржмржирзНржз ржХрж░рж╛ рж╣рж▓рзЛ!</b>\n\nтЬЕ ржПржЦржи рж╕рж╛ржзрж╛рж░ржг User рж░рж╛ Bot ржУржкрзЗржи ржХрж░рж▓рзЗ Update ржорзЗрж╕рзЗржЬ ржжрзЗржЦржмрзЗ!\n"
        "тЬЕ рждрзЛржорж╛рж░ Admin ID (" + str(ADMIN_ID) + ") рждрзЗ рж╕ржм ржЪрж▓ржмрзЗ, Admin Panel ржУ ржЪрж▓ржмрзЗ!", parse_mode="HTML")

async def h_permoff(update, context):
    """/parmanetbotoff -> bot is OFF for everybody except the admin until /startbot."""
    if not _is_admin_update(update): return
    with _lock:
        d = load(); settings_of(d)["bot_perm_off"] = True; save(d)
    await update.effective_message.reply_text(
        "тЫФ <b>Bot ржкрж╛рж░рзНржорж╛ржирзЗржирзНржЯрж▓рж┐ ржмржирзНржз ржХрж░рж╛ рж╣рж▓рзЛ!</b>\n\n"
        "тЬЕ рж╕рж╛ржзрж╛рж░ржг User /start ржжрж┐рж▓рзЗ ржмрж╛ ржмржЯ ржУржкрзЗржи ржХрж░рж▓рзЗ рж╢рзБржзрзБ \"ржХрж╛ржЬ ржПржЦржи ржмржирзНржз ржЖржЫрзЗ\" ржорзЗрж╕рзЗржЬ ржжрзЗржЦржмрзЗред\n"
        "тЬЕ ржнрзЛрж░ рзмржЯрж╛рж░ Good Morning ржорзЗрж╕рзЗржЬ ржЖрж░ рж▓рж┐ржорж┐ржЯ ржмржжрж▓ ржмржирзНржз ржерж╛ржХржмрзЗред\n"
        "тЬЕ рждрзЛржорж╛рж░ Admin ID (" + str(ADMIN_ID) + ") рждрзЗ рж╕ржм ржЪрж▓ржмрзЗред\n\n"
        "ЁЯЯв ржЖржмрж╛рж░ ржЪрж╛рж▓рзБ ржХрж░рждрзЗ: /startbot", parse_mode="HTML")

async def h_startbot(update, context):
    if not _is_admin_update(update): return
    with _lock:
        d = load(); _s = settings_of(d); _s["bot_stopped"] = False; _s["bot_perm_off"] = False; save(d)
    uname_ = context.bot.username or ""
    btn = ("тЦ╢я╕П /start", "https://t.me/" + uname_ + "?start=live") if uname_ else None
    started = start_broadcast(live_html(), button=btn, report_to=update.effective_user.id, label="BOT LIVE ржирзЛржЯрж┐рж╢")
    await update.effective_message.reply_text(
        "тЬЕ <b>Bot ржЪрж╛рж▓рзБ ржХрж░рж╛ рж╣рж▓рзЛ!</b>\n\nЁЯУв " + ("рж╕ржм User-ржХрзЗ ржЪрж╛рж▓рзБ рж╣ржУржпрж╝рж╛рж░ ржирзЛржЯрж┐рж╢ ржкрж╛ржарж╛ржирзЛ рж╣ржЪрзНржЫрзЗ... (рж╢рзЗрж╖ рж╣рж▓рзЗ рж░рж┐ржкрзЛрж░рзНржЯ ржЖрж╕ржмрзЗ)" if started else "ржЖрж░рзЗржХржЯрж╛ Broadcast ржЪрж▓ржЫрзЗ, рждрж╛ржЗ ржирзЛржЯрж┐рж╢ ржкрж╛ржарж╛ржирзЛ рж╣ржпрж╝ржирж┐ред"), parse_mode="HTML")

async def h_notice_ask(update, context):
    """fixed notices: ask the admin to confirm first (the menu can be tapped by mistake)."""
    if not _is_admin_update(update): return
    cmd = (update.effective_message.text or "").split()[0].lstrip("/").split("@")[0].lower()
    with _lock:
        d = load(); s = settings_of(d); html = notice_msg(cmd, s)
    if not html: return
    await update.effective_message.reply_text("ЁЯСА <b>Preview</b> тАФ рж╕ржмрж╛ржЗржХрзЗ ржкрж╛ржарж╛ржмрзЗржи?\n\n" + html, parse_mode="HTML",
                                              reply_markup=_mk([[("тЬЕ рж╕ржмрж╛ржЗржХрзЗ ржкрж╛ржарж╛ржи", {"cb": "bc:" + cmd}), ("тЭМ ржмрж╛рждрж┐рж▓", {"cb": "bcx"})]]))

async def h_bc_cb(update, context):
    q = update.callback_query
    if not q or int(q.from_user.id) != ADMIN_ID:
        if q: await q.answer("тЫФ", show_alert=False)
        return
    data = q.data or ""
    if data == "bcx":
        await q.answer("ржмрж╛рждрж┐рж▓"); await q.edit_message_text("тЭМ ржмрж╛рждрж┐рж▓ ржХрж░рж╛ рж╣ржпрж╝рзЗржЫрзЗред"); return
    key = data.split(":", 1)[1] if ":" in data else ""
    with _lock:
        d = load(); s = settings_of(d); html = notice_msg(key, s)
    if not html: await q.answer("?"); return
    btn = None
    if key == "newstart":
        uname_ = context.bot.username or ""
        btn = ("ЁЯЖХ New Start", "https://t.me/" + uname_ + "?start=new") if uname_ else None
    started = start_broadcast(html, button=btn, report_to=q.from_user.id, label=NOTICE_LABEL.get(key, "Notice"))
    await q.answer("рж╢рзБрж░рзБ рж╣ржпрж╝рзЗржЫрзЗ" if started else "ржЖрж░рзЗржХржЯрж╛ Broadcast ржЪрж▓ржЫрзЗ")
    await q.edit_message_text(("ЁЯУв <b>" + NOTICE_LABEL.get(key, "Notice") + "</b> ржкрж╛ржарж╛ржирзЛ рж╢рзБрж░рзБ рж╣ржпрж╝рзЗржЫрзЗ... (рж╢рзЗрж╖ рж╣рж▓рзЗ рж░рж┐ржкрзЛрж░рзНржЯ ржЖрж╕ржмрзЗ)") if started else "тП│ ржЖрж░рзЗржХржЯрж╛ Broadcast ржЪрж▓ржЫрзЗ, ржПржХржЯрзБ ржкрж░рзЗ ржЖржмрж╛рж░ ржЪрзЗрж╖рзНржЯрж╛ ржХрж░рзБржиред", parse_mode="HTML")

def fancy2(title, body, e1="ЁЯТО", e2="ЁЯТ░"):
    return ("тФПтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФУ\n  " + e1 + " <b>" + title + "</b> " + e2 + "\nтФЧтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФЫ\n\n" + body +
            "\n\nтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА\nЁЯдЦ <b>" + BRAND + "</b>")

# keyword -> (words, emoji, closing line).  Works for Bangla and Banglish words.
STYLE_CATS = [
    (["problem", "somossa", "somosya", "рж╕ржорж╕рзНржпрж╛", "error", "issue", "bug", "ржЭрж╛ржорзЗрж▓рж╛", "jhamela"], "тЪая╕П", "ЁЯЩП ржЕрж╕рзБржмрж┐ржзрж╛рж░ ржЬржирзНржп ржжрзБржГржЦрж┐ржд, ржжрзНрж░рзБржд рж╕ржорж╛ржзрж╛ржирзЗрж░ ржЪрзЗрж╖рзНржЯрж╛ ржЪрж▓ржЫрзЗ ЁЯЫая╕П"),
    (["deri", "ржжрзЗрж░рж┐", "ржжрзЗрж░рзА", "late", "delay", "wait", "ржЕржкрзЗржХрзНрж╖рж╛", "opekkha", "soon", "рж╢рзАржШрзНрж░ржЗ"], "тП│", "ЁЯЩП ржПржХржЯрзБ ржзрзИрж░рзНржп ржзрж░рзБржи, ржжрзЗрж░рж┐рж░ ржЬржирзНржп ржЖржирзНрждрж░рж┐ржХржнрж╛ржмрзЗ ржжрзБржГржЦрж┐ржд ЁЯТЭ"),
    (["running", "cholche", "cholse", "ржЪрж▓ржЫрзЗ", "ржЪрж▓ржорж╛ржи", "processing"], "ЁЯФД", "тП│ ржзрж╛ржкрзЗ ржзрж╛ржкрзЗ рж╕ржмрж╛рж░ ржкрзЗржорзЗржирзНржЯ ржжрзЗржУржпрж╝рж╛ рж╣ржЪрзНржЫрзЗред"),
    (["complete", "completed", "done", "sent", "pathano", "pathiye", "pathaisi", "ржкрж╛ржарж╛ржирзЛ", "ржкрж╛ржарж┐ржпрж╝рзЗ", "clear", "ржХрзНрж▓рж┐ржпрж╝рж╛рж░", "рж╕ржорзНржкржирзНржи", "paid", "рж╣ржпрж╝рзЗ ржЧрзЗржЫрзЗ", "hoye gese", "hoye geche", "ржХрж░рж╛ рж╣ржпрж╝рзЗржЫрзЗ"], "тЬЕ", "ЁЯФФ рж╕ржмрж╛ржЗ ржирж┐ржЬрзЗрж░ ржПржХрж╛ржЙржирзНржЯ ржЪрзЗржХ ржХрж░рзБржи ЁЯТЭ"),
    (["withdraw", "ржЙржЗржержбрзНрж░", "withdrawal", "request", "рж░рж┐ржХрзЛржпрж╝рзЗрж╕рзНржЯ"], "ЁЯТ╕", "ЁЯТ╕ Withdraw рж╕ржВржХрзНрж░рж╛ржирзНржд ржЖржкржбрзЗржЯржЯрж╛ ржнрж╛рж▓рзЛржнрж╛ржмрзЗ ржжрзЗржЦрзЗ ржирж┐ржиред"),
    (["update", "ржЖржкржбрзЗржЯ", "notun", "ржирждрзБржи"], "ЁЯЖХ", "ЁЯУв ржирждрзБржи ржЖржкржбрзЗржЯ ржкрзЗрждрзЗ Channel ржП ржерж╛ржХрзБржиред"),
    (["sorry", "khoma", "ржХрзНрж╖ржорж╛", "ржжрзБржГржЦрж┐ржд", "dukkhito", "dukhito"], "ЁЯЩП", "ЁЯТЭ ржЖржкржирж╛ржжрзЗрж░ рж╕рж╣ржпрзЛржЧрж┐рждрж╛рж░ ржЬржирзНржп ржзржирзНржпржмрж╛ржжред"),
    (["thanks", "thank", "dhonnobad", "ржзржирзНржпржмрж╛ржж"], "ЁЯЩП", "ЁЯТЭ Thanks for your support"),
    (["bonus", "offer", "ржмрзЛржирж╛рж╕", "ржЕржлрж╛рж░", "gift", "ржЧрж┐ржлржЯ"], "ЁЯОБ", "ЁЯОЙ рж╕рзБржпрзЛржЧржЯрж╛ ржХрж╛ржЬрзЗ рж▓рж╛ржЧрж╛ржи!"),
    (["rule", "rules", "ржирж┐ржпрж╝ржо", "рж░рзБрж▓рж╕", "warning", "рж╕рждрж░рзНржХ", "ban", "ржмрзНржпрж╛ржи"], "ЁЯУЬ", "ЁЯСА ржирж┐ржпрж╝ржо ржорзЗржирзЗ ржХрж╛ржЬ ржХрж░рзБржи, ржзржирзНржпржмрж╛ржжред"),
]
STYLE_BASE = {"payment": ("PAYMENT NOTICE", "ЁЯТ│"), "important": ("IMPORTANT NOTICE", "тЪая╕П"), "hello": ("HELLO EVERYONE", "ЁЯСЛ")}

def style_notice(kind, text):
    """admin writes plain text -> stylish message, emoji chosen from what the text means."""
    raw = (text or "").strip(); t = raw.lower()
    hits = [(e, c) for words, e, c in STYLE_CATS if any(w in t for w in words)]
    title, base_e = STYLE_BASE.get(kind, ("NOTICE", "ЁЯУг"))
    lead = hits[0][0] if hits else base_e
    extra = " ".join(dict.fromkeys(e for e, _ in hits[1:3] if e != lead))
    body = lead + " <b>" + hesc(raw) + "</b>" + ((" " + extra) if extra else "")
    closings = list(dict.fromkeys(c for _, c in hits[:2]))
    if closings: body += "\n\n" + "\n".join(closings)
    return fancy2(title, body, base_e, "ЁЯТО")

async def h_styled(update, context):
    """/payment <text>   /important <text>   /hello <text>  -> stylish broadcast. No text = old fixed notice (preview)."""
    if not _is_admin_update(update): return
    cmd = (update.effective_message.text or "").split()[0].lstrip("/").split("@")[0].lower()
    a = _args_text(update, 1)
    if not a:
        if cmd == "important":
            await update.effective_message.reply_text("тЬНя╕П ржмрзНржпржмрж╣рж╛рж░: /important ржЖржкржирж╛рж░ рж▓рзЗржЦрж╛ (ржпрзЗржоржи: /important ржЖржЬ рж░рж╛рждрзЗ ржмржЯ ржЖржкржбрзЗржЯ рж╣ржмрзЗ)"); return
        return await h_notice_ask(update, context)
    started = start_broadcast(style_notice(cmd, a[0]), report_to=update.effective_user.id, label=cmd.upper())
    await update.effective_message.reply_text("ЁЯУв рж╕ржмрж╛ржЗржХрзЗ ржкрж╛ржарж╛ржирзЛ рж╢рзБрж░рзБ рж╣ржпрж╝рзЗржЫрзЗ... (рж╢рзЗрж╖ рж╣рж▓рзЗ рж░рж┐ржкрзЛрж░рзНржЯ ржЖрж╕ржмрзЗ)" if started else "тП│ ржЖрж░рзЗржХржЯрж╛ Broadcast ржЪрж▓ржЫрзЗ, ржПржХржЯрзБ ржкрж░рзЗ ржЖржмрж╛рж░ ржЪрзЗрж╖рзНржЯрж╛ ржХрж░рзБржиред")

async def h_custom(update, context):
    """/alltopicsms <text> -> your text goes to everybody exactly as written (no style, no header)."""
    if not _is_admin_update(update): return
    a = _args_text(update, 1)
    if not a:
        await update.effective_message.reply_text("тЬНя╕П ржмрзНржпржмрж╣рж╛рж░: /alltopicsms ржЖржкржирж╛рж░ рж▓рзЗржЦрж╛ ржорзЗрж╕рзЗржЬ"); return
    started = start_broadcast(hesc(a[0]), report_to=update.effective_user.id, label="Message")
    await update.effective_message.reply_text("ЁЯУв рж╕ржмрж╛ржЗржХрзЗ ржкрж╛ржарж╛ржирзЛ рж╢рзБрж░рзБ рж╣ржпрж╝рзЗржЫрзЗ... (рж╢рзЗрж╖ рж╣рж▓рзЗ рж░рж┐ржкрзЛрж░рзНржЯ ржЖрж╕ржмрзЗ)" if started else "тП│ ржЖрж░рзЗржХржЯрж╛ Broadcast ржЪрж▓ржЫрзЗ, ржПржХржЯрзБ ржкрж░рзЗ ржЖржмрж╛рж░ ржЪрзЗрж╖рзНржЯрж╛ ржХрж░рзБржиред")

def _fmt_rate(v):
    v = round(float(v), 4)
    return ("%.2f" % v) if abs(v * 100 - round(v * 100)) < 1e-9 else ("%g" % v)

async def h_setrate(update, context):
    """/watchrate 0.10   /autorate 0.05  -> sets that ad reward AND tells everybody (Rate Up / Rate Down style).
       No number = old behaviour (preview of the current rate)."""
    if not _is_admin_update(update): return
    cmd = (update.effective_message.text or "").split()[0].lstrip("/").split("@")[0].lower()
    if not context.args:
        return await h_notice_ask(update, context)
    try:
        new = float(context.args[0].replace(",", ".")); assert 0 < new <= 1000
    except Exception:
        await update.effective_message.reply_text("тЬНя╕П ржмрзНржпржмрж╣рж╛рж░: /" + cmd + " 0.10"); return
    key, name, icon = ("reward_watch", "Watch Ads", "тЦ╢я╕П") if cmd == "watchrate" else ("reward_auto", "Auto Ads", "тЪб")
    with _lock:
        d = load(); st = settings_of(d); old = float(st.get(key, 0) or 0)
        st[key] = round(new, 4); save(d)
    n, o = _fmt_rate(new), _fmt_rate(old)
    if new > old:
        html = fancy2(name.upper() + " RATE UP", "ЁЯФ║ <b>" + name + " рж░рзЗржЯ ржЖржк ржХрж░рж╛ рж╣ржпрж╝рзЗржЫрзЗ!</b> ЁЯОЙ\n\n" + icon + " ржПржЦржи ржкрзНрж░рждрж┐ржЯрж╛ " + name[:-4].strip() + " Ad-ржП ржкрж╛ржмрзЗржи: <b>" + n + " TK</b> ЁЯТ░\n\n"
                      "тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\nЁЯФе ржПржЦржиржЗ ржХрж╛ржЬ ржХрж░рзБржи, тП│ рж░рзЗржЯ ржкрж░рзЗ ржХржорзЗ ржпрзЗрждрзЗ ржкрж╛рж░рзЗ!", "ЁЯФ║", icon)
    elif new < old:
        html = fancy2(name.upper() + " RATE DOWN", "ЁЯФ╗ <b>" + name + " рж░рзЗржЯ ржбрж╛ржЙржи ржХрж░рж╛ рж╣ржпрж╝рзЗржЫрзЗ</b>\n\n" + icon + " ржПржЦржи ржкрзНрж░рждрж┐ржЯрж╛ " + name[:-4].strip() + " Ad-ржП ржкрж╛ржмрзЗржи: <b>" + n + " TK</b> ЁЯТ░\n\n"
                      "тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\nЁЯЩП рж╕ржмрж╛ржЗ ржХрж╛ржЬ ржЪрж╛рж▓рж┐ржпрж╝рзЗ ржпрж╛ржи, рж╕рж╣ржпрзЛржЧрж┐рждрж╛рж░ ржЬржирзНржп ржзржирзНржпржмрж╛ржж ЁЯТЭ", "ЁЯФ╗", icon)
    else:
        html = fancy2(name.upper() + " RATE", icon + " " + name + " рж░рзЗржЯ ржПржЦржи: <b>" + n + " TK</b> ЁЯТ░", icon, "ЁЯТ░")
    started = start_broadcast(html, report_to=update.effective_user.id, label=name + " Rate")
    await update.effective_message.reply_text("тЬЕ " + name + " рж░рзЗржЯ: " + o + " тЖТ <b>" + n + " TK</b>\nЁЯУв " + ("рж╕ржмрж╛ржЗржХрзЗ ржкрж╛ржарж╛ржирзЛ рж╢рзБрж░рзБ рж╣ржпрж╝рзЗржЫрзЗ..." if started else "ржЖрж░рзЗржХржЯрж╛ Broadcast ржЪрж▓ржЫрзЗ, ржирзЛржЯрж┐рж╢ ржпрж╛ржпрж╝ржирж┐ (рж░рзЗржЯ рж╕рзЗржн рж╣ржпрж╝рзЗржЫрзЗ)ред"), parse_mode="HTML")

ADMIN_COMMANDS = [("start", "ЁЯЪА ржмржЯ ржЪрж╛рж▓рзБ ржХрж░рзБржи"), ("newstart", "ЁЯдЦ Bot notun update hoyese"),
                  ("hello", "ЁЯСЛ Hello everyone kaj koren sobai"), ("bednotice", "ЁЯУв Broadcast bed notice"),
                  ("autorate", "тЪб Auto Ads Rate (/autorate 0.05)"), ("watchrate", "тЦ╢я╕П Watch Ads Rate (/watchrate 0.10)"),
                  ("alltopicsms", "ЁЯУЭ рж╕ржмрж╛ржЗржХрзЗ рж╕рж╛ржзрж╛рж░ржг ржорзЗрж╕рзЗржЬ (/alltopicsms рж▓рзЗржЦрж╛)"), ("important", "тЪая╕П Important Notice (/important рж▓рзЗржЦрж╛)"),
                  ("payment", "ЁЯТ│ Payment Notice (/payment рж▓рзЗржЦрж╛)"), ("payrunning", "ЁЯФД Payment Running"), ("allpayment", "тЬЕ All Payment Complete"),
                  ("parmanetbotoff", "тЫФ Parmanet Bot Off (ржХрж╛ржЬ ржмржирзНржз)"), ("stopbot", "ЁЯЫС Bot ржмржирзНржз ржХрж░рзБржи"), ("startbot", "ЁЯЯв Bot ржЪрж╛рж▓рзБ + рж╕ржмрж╛ржЗржХрзЗ ржирзЛржЯрж┐рж╢")]

def build_tg_app():
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", h_start))
    application.add_handler(CommandHandler(["stopbot", "botupdate", "stopped", "stop", "botstop"], h_stopbot))
    application.add_handler(CommandHandler(["parmanetbotoff", "permanentbotoff", "parmanentbotoff"], h_permoff))
    application.add_handler(CommandHandler(["startbot", "started", "botstart"], h_startbot))
    application.add_handler(CommandHandler(["payrunning", "allpayment", "newstart", "bednotice"], h_notice_ask))
    application.add_handler(CommandHandler(["payment", "important", "hello"], h_styled))
    application.add_handler(CommandHandler(["autorate", "watchrate"], h_setrate))
    application.add_handler(CommandHandler("alltopicsms", h_custom))
    application.add_handler(CommandHandler("id", h_id))
    application.add_handler(CallbackQueryHandler(h_bc_cb, pattern=r"^bc"))
    return application

@app.route('/cronjobs')
def cronjobs_route():
    import sys, cronjobs
    return cronjobs.handle(request, sys.modules[__name__])

@app.route('/webhook', methods=['POST'])
def webhook():
    if not BOT_TOKEN:
        return "BOT_TOKEN missing", 500
    try:
        from telegram import Update
        import asyncio
        data = request.get_json(force=True)
        application = build_tg_app()
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
        return "тЭМ BOT_TOKEN missing in Render Environment", 500
    try:
        import asyncio
        from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
        async def run():
            application = build_tg_app()
            await application.initialize()
            url = f"{WEBAPP_URL}/webhook"
            result = await application.bot.set_webhook(url=url)
            me = await application.bot.get_me()
            menu = "ok"
            try:   # normal users see only /start, the admin sees the full command menu
                await application.bot.set_my_commands([BotCommand("start", "ЁЯЪА ржмржЯ ржЪрж╛рж▓рзБ ржХрж░рзБржи")], scope=BotCommandScopeDefault())
                await application.bot.set_my_commands([BotCommand(c, d) for c, d in ADMIN_COMMANDS], scope=BotCommandScopeChat(chat_id=ADMIN_ID))
            except Exception as e: menu = "menu error: " + str(e)
            await application.shutdown()
            return result, me, menu
        result, me, menu = asyncio.run(run())
        return f"тЬЕ Webhook set!<br>Bot: @{me.username}<br>URL: {WEBAPP_URL}/webhook<br>Result: {result}<br>Command menu: {menu}<br><br><a href='/'>Go to App</a>"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"тЭМ Failed: {e}", 500

# ---- when the admin stops the bot, the mini-app is closed for normal users (admin still works) ----
@app.before_request
def maintenance_gate():
    if not request.path.startswith("/api/"): return None
    u = tg_user()
    if not u or is_admin(u): return None
    with _lock:
        _st = settings_of(load()); stopped = bool(_st.get("bot_stopped")) or bool(_st.get("bot_perm_off")); perm = bool(_st.get("bot_perm_off"))
    if stopped: return jsonify(error="maintenance", perm=perm)
    return None

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
    <h2>тЬЕ Bot Check - V4 Direct Read</h2>
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
ADMIN_ID = int(os.getenv("ADMIN_ID", "6560485203"))
DATA_FILE = os.getenv("DATA_FILE", "/tmp/atm_data.json")  # NOT inside BASE_DIR, so static route can't serve it
AD_MIN_SECONDS = float(os.getenv("AD_MIN_SECONDS", "15"))  # server-side check: ad reward only after this many seconds
_lock = threading.Lock()
DEFAULT_GUIDELINES = ("1. Watch ads daily to earn 0.50 TK per ad\n"
                      "2. Use VPN from KAJER VPN button for more ads\n"
                      "3. Refer friends to get 10% bonus\n"
                      "4. Confirm Pending Balance after 500 ads\n"
                      "5. Contact admin for support")
DEFAULTS = {"settings": {"reward_watch": 0.5, "reward_auto": 0.10, "limit_watch": 100, "limit_auto": 100,
                         "notice": "ЁЯУв VPN diye kaj korbe",
                         "country_notice": "тЪая╕П {country} VPN/Proxy on korun, tarpor ad dekhun. Apnar current country: {current}",
                         "ref_bonus": 10,
                         "min": {"bkash": 0, "nagad": 0, "rocket": 0, "binance": 0, "recharge": 0}, "vpn_country": "",
                         "bot_guidelines": DEFAULT_GUIDELINES,
                         # ====== NEW notice system ======
                         # Welcome popup тАФ shown to a user once per notice_version when they open the bot.
                         "welcome_notice": "",
                         "welcome_btn_text": "Click Here",
                         "welcome_btn_url": "",
                         # Thin red banner тАФ broadcasts to active users immediately when notice_version bumps.
                         "notice_banner": "",
                         # notice_version: incremented every time admin saves a notice. Users store the version they last saw.
                         "notice_version": 1,
                         "usdt_rate": 123.0,
                         "confirm_ads": 500, "claim_ads": 5, "bot_stopped": False, "bot_perm_off": False, "next_limit_watch": None, "next_limit_auto": None, "morning_done": "", "claim_enabled": True, "claim_gap_min": 2.0, "notice_every": 5,
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
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")  # day resets at 6:00 AM Bangladesh time (00:00 UTC)

def new_bal():
    return {"main": 0.0, "pending": 0.0, "today_ads": 0, "total_ads": 0, "watch_today": 0, "auto_today": 0, "day": today_key(),
            # Lifetime counters тАФ never reset by admin "Reset Ads". Used by profile page.
            "lifetime_earned": 0.0, "lifetime_ads": 0,
            # Lifetime WATCH-ad counter тАФ used to detect every 5th watch ad (5, 10, 15...) for the special popup.
            "lifetime_watch_ads": 0,
            # Confirm-Pending system: cfill = ads counted toward the yellow bar, cclaim = confirm-ads already watched in the unlock stage
            "cfill": 0, "cclaim": 0}

def roll(rec):
    b = rec["bal"]
    if b.get("day") != today_key(): b.update(day=today_key(), today_ads=0, watch_today=0, auto_today=0)

def state(rec):
    roll(rec); b = rec["bal"]
    # Backfill lifetime fields for old accounts that don't have them yet
    if "lifetime_earned" not in b: b["lifetime_earned"] = round(float(b.get("main", 0)) + float(b.get("pending", 0)), 4)
    if "lifetime_ads" not in b: b["lifetime_ads"] = int(b.get("total_ads", 0))
    if "lifetime_watch_ads" not in b: b["lifetime_watch_ads"] = int(b.get("watch_today", 0))
    if "cfill" not in b: b["cfill"] = int(b.get("total_ads", 0))   # old accounts keep their current bar progress
    if "cclaim" not in b: b["cclaim"] = 0
    return {"main": round(b["main"], 2), "pending": round(b["pending"], 2), "today_ads": b["today_ads"], "total_ads": b["total_ads"],
            "watch_today": b["watch_today"], "auto_today": b["auto_today"],
            "lifetime_earned": round(b.get("lifetime_earned", 0), 2), "lifetime_ads": int(b.get("lifetime_ads", 0)),
            "lifetime_watch_ads": int(b.get("lifetime_watch_ads", 0)),
            "cfill": int(b.get("cfill", 0)), "cclaim": int(b.get("cclaim", 0)),
            "joined": int(rec.get("joined", 0))}

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
FLAG = {"US":"ЁЯЗ║ЁЯЗ╕","CA":"ЁЯЗиЁЯЗж","GB":"ЁЯЗмЁЯЗз","AU":"ЁЯЗжЁЯЗ║","BD":"ЁЯЗзЁЯЗй","IN":"ЁЯЗоЁЯЗ│","DE":"ЁЯЗйЁЯЗк","SG":"ЁЯЗ╕ЁЯЗм","MY":"ЁЯЗ▓ЁЯЗ╛","AE":"ЁЯЗжЁЯЗк",
        "SA":"ЁЯЗ╕ЁЯЗж","FR":"ЁЯЗлЁЯЗ╖","NL":"ЁЯЗ│ЁЯЗ▒","JP":"ЁЯЗпЁЯЗ╡","PK":"ЁЯЗ╡ЁЯЗ░","NZ":"ЁЯЗ│ЁЯЗ┐","IE":"ЁЯЗоЁЯЗк","SE":"ЁЯЗ╕ЁЯЗк","CH":"ЁЯЗиЁЯЗн","IT":"ЁЯЗоЁЯЗ╣",
        "ES":"ЁЯЗкЁЯЗ╕","RU":"ЁЯЗ╖ЁЯЗ║","BR":"ЁЯЗзЁЯЗ╖","MX":"ЁЯЗ▓ЁЯЗ╜","ZA":"ЁЯЗ┐ЁЯЗж","KR":"ЁЯЗ░ЁЯЗ╖","CN":"ЁЯЗиЁЯЗ│","ID":"ЁЯЗоЁЯЗй","PH":"ЁЯЗ╡ЁЯЗн","VN":"ЁЯЗ╗ЁЯЗ│",
        "TH":"ЁЯЗ╣ЁЯЗн","TR":"ЁЯЗ╣ЁЯЗ╖","EG":"ЁЯЗкЁЯЗм","NG":"ЁЯЗ│ЁЯЗм","AR":"ЁЯЗжЁЯЗ╖","CL":"ЁЯЗиЁЯЗ▒","CO":"ЁЯЗиЁЯЗ┤","PE":"ЁЯЗ╡ЁЯЗк","LK":"ЁЯЗ▒ЁЯЗ░","NP":"ЁЯЗ│ЁЯЗ╡",
        "BN":"ЁЯЗзЁЯЗ│","HK":"ЁЯЗнЁЯЗ░","TW":"ЁЯЗ╣ЁЯЗ╝","IL":"ЁЯЗоЁЯЗ▒","PT":"ЁЯЗ╡ЁЯЗ╣","AT":"ЁЯЗжЁЯЗ╣","BE":"ЁЯЗзЁЯЗк","DK":"ЁЯЗйЁЯЗ░","FI":"ЁЯЗлЁЯЗо","NO":"ЁЯЗ│ЁЯЗ┤",
        "PL":"ЁЯЗ╡ЁЯЗ▒","CZ":"ЁЯЗиЁЯЗ┐","GR":"ЁЯЗмЁЯЗ╖","HU":"ЁЯЗнЁЯЗ║","RO":"ЁЯЗ╖ЁЯЗ┤","BG":"ЁЯЗзЁЯЗм","HR":"ЁЯЗнЁЯЗ╖","SK":"ЁЯЗ╕ЁЯЗ░","SI":"ЁЯЗ╕ЁЯЗо","EE":"ЁЯЗкЁЯЗк",
        "LV":"ЁЯЗ▒ЁЯЗ╗","LT":"ЁЯЗ▒ЁЯЗ╣","UA":"ЁЯЗ║ЁЯЗж","BY":"ЁЯЗзЁЯЗ╛","KZ":"ЁЯЗ░ЁЯЗ┐","UZ":"ЁЯЗ║ЁЯЗ┐","QA":"ЁЯЗ╢ЁЯЗж","KW":"ЁЯЗ░ЁЯЗ╝","BH":"ЁЯЗзЁЯЗн","OM":"ЁЯЗ┤ЁЯЗ▓",
        "JO":"ЁЯЗпЁЯЗ┤","LB":"ЁЯЗ▒ЁЯЗз","IQ":"ЁЯЗоЁЯЗ╢","IR":"ЁЯЗоЁЯЗ╖","AF":"ЁЯЗжЁЯЗл","MM":"ЁЯЗ▓ЁЯЗ▓","KH":"ЁЯЗ░ЁЯЗн","LA":"ЁЯЗ▒ЁЯЗж","MO":"ЁЯЗ▓ЁЯЗ┤"}

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
    """same as tz_ok but returns True also when no tz data тАФ used internally for clarity."""
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
        out.append({"code": c, "name": CNAME.get(c, c), "flag": FLAG.get(c, "ЁЯП│я╕П")})
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
    primary = allowed_list[0] if allowed_list else {"code": "", "name": "тАФ", "flag": "ЁЯП│я╕П"}
    c_ok = country_ok(allowed, code, name)
    t_ok = tz_ok(allowed, phone_tz)
    # Headline message
    if not c_ok and not t_ok:
        msg = "ржЖржкржирж╛рж░ IP рж▓рзЛржХрзЗрж╢ржи ржПржмржВ ржлрзЛржирзЗрж░ ржЯрж╛ржЗржо ржЬрзЛржи ржирж┐рж░рзНржмрж╛ржЪрж┐ржд рж╕рж╛рж░рзНржнрж╛рж░рзЗрж░ рж╕рж╛ржерзЗ ржорж┐рж▓ржЫрзЗ ржирж╛ред"
        hint = "VPN/Proxy ржЕржи ржХрж░рзБржи ржПржмржВ ржлрзЛржирзЗрж░ Settings тЖТ ржЯрж╛ржЗржо ржЬрзЛржи ржкрж░рж┐ржмрж░рзНрждржи ржХрж░рзБржиред"
    elif not c_ok:
        msg = "ржЖржкржирж╛рж░ IP рж▓рзЛржХрзЗрж╢ржи ржирж┐рж░рзНржмрж╛ржЪрж┐ржд рж╕рж╛рж░рзНржнрж╛рж░рзЗрж░ рж╕рж╛ржерзЗ ржорж┐рж▓ржЫрзЗ ржирж╛ред"
        hint = "VPN/Proxy ржЕржи ржХрж░рзБржи ржПржмржВ ржЕржирзБржорзЛржжрж┐ржд ржжрзЗрж╢ рж╕рж┐рж▓рзЗржХрзНржЯ ржХрж░рзБржиред"
    elif not t_ok:
        msg = "ржЖржкржирж╛рж░ ржлрзЛржирзЗрж░ ржЯрж╛ржЗржо ржЬрзЛржи ржирж┐рж░рзНржмрж╛ржЪрж┐ржд рж╕рж╛рж░рзНржнрж╛рж░рзЗрж░ рж╕рж╛ржерзЗ ржорж┐рж▓ржЫрзЗ ржирж╛ред"
        hint = "ржлрзЛржирзЗрж░ Settings тЖТ ржЯрж╛ржЗржо ржЬрзЛржи ржкрж░рж┐ржмрж░рзНрждржи ржХрж░рзБржиред (VPN ржЕржи ржерж╛ржХрж▓рзЗржУ ржЯрж╛ржЗржо ржЬрзЛржи ржарж┐ржХ ржХрж░рждрзЗ рж╣ржмрзЗ)"
    else:
        msg = "рж▓рзЛржХрзЗрж╢ржи ржпрж╛ржЪрж╛ржЗ ржмрзНржпрж░рзНрже рж╣ржпрж╝рзЗржЫрзЗред"
        hint = ""
    return jsonify(error="country", notice=msg, hint=hint,
                   selected_server=primary,
                   allowed_countries=allowed_list,
                   current_country={"code": code, "name": name or (CNAME.get(code, "") if code else ""), "flag": FLAG.get(code, "ЁЯП│я╕П") if code else "ЁЯП│я╕П"},
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
                # ===== NEW notice system: bump version whenever any notice field changes =====
                _notice_changed = False
                if "welcome_notice" in s:
                    v = str(s["welcome_notice"])[:1500]
                    if cur.get("welcome_notice","") != v: _notice_changed = True
                    cur["welcome_notice"] = v
                if "welcome_btn_text" in s: cur["welcome_btn_text"] = str(s["welcome_btn_text"])[:60]
                if "welcome_btn_url" in s: cur["welcome_btn_url"] = str(s["welcome_btn_url"])[:500]
                if "notice_banner" in s:
                    v = str(s["notice_banner"])[:300]
                    if cur.get("notice_banner","") != v: _notice_changed = True
                    cur["notice_banner"] = v
                if "notice_version" in s:
                    try: cur["notice_version"] = max(1, int(float(s["notice_version"])))
                    except Exception: pass
                elif _notice_changed:
                    # Auto-bump version so all users see a "new notice" indicator (red bell + banner).
                    cur["notice_version"] = int(cur.get("notice_version", 1) or 1) + 1
                if "home_notice" in s: cur["home_notice"] = str(s["home_notice"])[:500]
                if "usdt_rate" in s: cur["usdt_rate"] = max(0.0, float(s["usdt_rate"]))
                if "payment_methods" in s and isinstance(s["payment_methods"], dict):
                    for mk in ("bkash","nagad","rocket","binance","recharge"):
                        if mk in s["payment_methods"]:
                            cur["payment_methods"][mk] = bool(s["payment_methods"][mk])
                if "confirm_ads" in s: cur["confirm_ads"] = max(1, int(float(s["confirm_ads"])))
                if "claim_enabled" in s: cur["claim_enabled"] = bool(s["claim_enabled"])
                if "claim_gap_min" in s: cur["claim_gap_min"] = min(1440.0, max(0.0, float(s["claim_gap_min"])))
                if "claim_ads" in s: cur["claim_ads"] = max(1, int(float(s["claim_ads"])))
                if "notice_every" in s: cur["notice_every"] = max(1, int(float(s["notice_every"])))
                if "ref_bonus" in s: cur["ref_bonus"] = min(100.0, max(0.0, float(s["ref_bonus"])))
                for k in ("limit_watch", "limit_auto"):
                    if k in s: cur[k] = max(0, int(float(s[k])))
                for k in ("next_limit_watch", "next_limit_auto"):      # tomorrow's limits, applied by /cronjobs at 6:00 AM
                    if k in s: cur[k] = None if s[k] in (None, "") else max(0, int(float(s[k])))
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
        # ===== Notice system: tell the client if there is an unseen notice (so bell turns red + banner shows) =====
        cur_ver = int(s.get("notice_version", 1) or 1)
        user_ver = int(rec.get("last_notice_version", 0) or 0)
        has_new = cur_ver > user_ver
        notice_info = {
            "version": cur_ver,
            "has_new": has_new,
            "welcome_text": str(s.get("welcome_notice", "") or ""),
            "welcome_btn_text": str(s.get("welcome_btn_text", "") or ""),
            "welcome_btn_url": str(s.get("welcome_btn_url", "") or ""),
            "banner": str(s.get("notice_banner", "") or ""),
        }
        return jsonify(ok=True, banned=False, migrated=migrated, state=state(rec), settings=s,
                       country={"code": code, "name": name, "ok": loc_ok, "country_ok": c_ok, "tz_ok": t_ok,
                                "phone_tz": phone_tz, "allowed": allowed_display(allowed), "ip": client_ip()},
                       notice=notice_info,
                       refs=ref_stats(d, uid), withdraws=user_withdraws(d, uid), is_admin=is_admin(u))

@app.route('/api/notice/seen', methods=['POST'])
def api_notice_seen():
    """Marks the current notice_version as seen by this user (so bell no longer red, banner stops)."""
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); s = settings_of(d); rec = ensure_user(d, u)
        if rec.get("banned"): return jsonify(error="banned")
        cur_ver = int(s.get("notice_version", 1) or 1)
        rec["last_notice_version"] = cur_ver
        save(d)
    return jsonify(ok=True, version=cur_ver)

# ---------- User Ads Tracker (admin panel): views / clicks per user ----------
TRACK_CLICK_SECONDS = float(os.getenv("TRACK_CLICK_SECONDS", "25"))   # user back after >= this many seconds => View + Click
ONLINE_SECONDS = 90                                                    # bot pings /api/me every 30s, so 90s = online

def trk_of(rec):
    t = rec.setdefault("trk", {})
    for k in ("v_all", "c_all", "v_today", "c_today"): t.setdefault(k, 0)
    t.setdefault("hist", []); t.setdefault("day", today_key())
    if t["day"] != today_key(): t["day"] = today_key(); t["v_today"] = 0; t["c_today"] = 0   # daily reset 6:00 AM Bangladesh time
    return t

@app.route('/api/ad/track', methods=['POST'])
def api_ad_track():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    b = request.get_json(silent=True) or {}
    ev = b.get("ev"); now = time.time()
    if ev not in ("view", "back"): return jsonify(error="bad data"), 400
    with _lock:
        d = load(); rec = ensure_user(d, u); t = trk_of(rec)
        if ev == "view":
            # counted right before the ad is shown
            t["v_all"] += 1; t["v_today"] += 1; t["open_t"] = now
            t["hist"].append({"k": "view", "t": int(now)})
        else:
            ot = t.pop("open_t", None)
            if ot:
                elapsed = now - float(ot)
                try: away = min(float(b.get("away", 0)), elapsed)      # can never be more than the real time passed
                except Exception: away = 0.0
                if away >= TRACK_CLICK_SECONDS:                         # came back after 25s+ => it was a click too
                    t["c_all"] += 1; t["c_today"] += 1
                    t["hist"].append({"k": "click", "t": int(now)})
        t["hist"] = t["hist"][-60:]
        save(d)
    return jsonify(ok=True)

@app.route('/api/admin/tracker')
def api_admin_tracker():
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    now = time.time(); out = []
    with _lock:
        d = load()
        for r in d["users"].values():
            if now - float(r.get("last_seen", 0) or 0) > ONLINE_SECONDS: continue
            if r.get("banned"): continue
            t = trk_of(r); cc = r.get("country") or ""
            out.append({"id": r.get("id"), "name": r.get("name", ""), "username": r.get("username", ""),
                        "cc": cc, "flag": FLAG.get(cc, "ЁЯП│я╕П") if cc else "ЁЯП│я╕П",
                        "v_today": t["v_today"], "c_today": t["c_today"], "v_all": t["v_all"], "c_all": t["c_all"],
                        "hist": list(reversed(t["hist"][-12:]))})
    out.sort(key=lambda x: (x["name"] or "").lower())
    return jsonify(ok=True, online=len(out), users=out)

def confirm_gate(s, b, check_gap):
    """Rules for the Confirm-Pending ads. Returns an error dict, or None when the user may continue."""
    need = int(s.get("confirm_ads", 500))
    if not s.get("claim_enabled", True): return {"error": "claimoff"}
    if int(b.get("cfill", 0)) < need: return {"error": "locked", "need": need - int(b.get("cfill", 0))}
    if b["pending"] <= 0: return {"error": "nopending"}
    if check_gap and int(b.get("cclaim", 0)) > 0:
        gap = float(s.get("claim_gap_min", 2.0) or 0)
        wait = gap * 60 - (time.time() - float(b.get("cclaim_t", 0)))
        if wait > 0: return {"error": "cooldown", "wait": int(wait) + 1, "gap_min": gap}
    return None

@app.route('/api/confirm_check', methods=['POST'])
def api_confirm_check():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); s = settings_of(d); rec = ensure_user(d, u)
        if rec.get("banned"): return jsonify(error="banned")
        roll(rec); b = rec["bal"]
        if "cfill" not in b: b["cfill"] = int(b.get("total_ads", 0))
        if "cclaim" not in b: b["cclaim"] = 0
        err = confirm_gate(s, b, True)
        if err: return jsonify(**err)
        return jsonify(ok=True, step=int(b["cclaim"]) + 1, total=int(s.get("claim_ads", 5)))

@app.route('/api/ad/start', methods=['POST'])
def api_ad_start():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    body = request.get_json(silent=True) or {}
    t = body.get("type")
    phone_tz = str(body.get("phone_tz") or "").strip()
    if t not in ("watch", "auto", "confirm"): return jsonify(error="bad data"), 400
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
        if t == "confirm":
            if "cfill" not in b: b["cfill"] = int(b.get("total_ads", 0))
            if "cclaim" not in b: b["cclaim"] = 0
            err = confirm_gate(s, b, True)
            if err: return jsonify(**err)
            rec["ad"] = {"type": "confirm", "t": time.time(), "special": False}
            if phone_tz: rec["phone_tz"] = phone_tz[:60]
            save(d)
            return jsonify(ok=True, special=False)
        lim = s["limit_watch"] if t == "watch" else s["limit_auto"]
        if b[t + "_today"] >= lim: return jsonify(error="limit", type=t, limit=lim)
        # Detect every 5th WATCH ad (5, 10, 15...) for the special popup + 25s wait
        is_special = False
        if t == "watch":
            cur_watch = int(b.get("lifetime_watch_ads", 0))
            # (cur_watch + 1) is the ad number we are ABOUT to serve. If divisible by 5 тЖТ special.
            if (cur_watch + 1) % max(1, int(s.get("notice_every", 5) or 5)) == 0:
                is_special = True
        rec["ad"] = {"type": t, "t": time.time(), "special": is_special}
        if phone_tz: rec["phone_tz"] = phone_tz[:60]
        save(d)
    return jsonify(ok=True, special=is_special)

@app.route('/api/ad/claim', methods=['POST'])
def api_ad_claim():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); s = settings_of(d); rec = ensure_user(d, u)
        if rec.get("banned"): return jsonify(error="banned")
        ad = rec.get("ad")
        if not ad: return jsonify(error="noad")
        # Special 5th watch ad requires 25s wait; normal ads use AD_MIN_SECONDS (15s)
        is_special = bool(ad.get("special"))
        min_seconds = 25.0 if (is_special or ad.get("type") == "confirm") else AD_MIN_SECONDS
        wait = min_seconds - (time.time() - ad["t"])
        if wait > 0: return jsonify(error="early", wait=round(wait, 1))
        roll(rec); b = rec["bal"]; t = ad["type"]
        if "cfill" not in b: b["cfill"] = int(b.get("total_ads", 0))
        if "cclaim" not in b: b["cclaim"] = 0
        if t == "confirm":
            rec.pop("ad", None)
            need = int(s.get("confirm_ads", 500)); steps = max(1, int(s.get("claim_ads", 5)))
            err = confirm_gate(s, b, False)
            if err: save(d); return jsonify(**err)
            b["cclaim"] = int(b.get("cclaim", 0)) + 1; b["cclaim_t"] = time.time()
            done = b["cclaim"] >= steps
            if done:
                # all confirm-ads watched тЖТ pending moves to MAIN, bar empties, everything starts again
                b["main"] = round(b["main"] + b["pending"], 4); b["pending"] = 0.0
                b["cclaim"] = 0; b["cfill"] = max(0, int(b["cfill"]) - need)
            save(d)
            return jsonify(ok=True, state=state(rec), reward=0, to_main=False, special=False, confirm_done=done, claim_step=(steps if done else b["cclaim"]), claim_total=steps)
        lim = s["limit_watch"] if t == "watch" else s["limit_auto"]
        rec.pop("ad", None)
        if b[t + "_today"] >= lim:
            save(d); return jsonify(error="limit", type=t, limit=lim)
        reward = float(s["reward_watch"] if t == "watch" else s["reward_auto"])
        # WATCH ad reward тЖТ goes DIRECTLY to MAIN balance (not pending).
        # AUTO ad reward тЖТ still goes to PENDING balance (as before).
        if t == "watch":
            b["main"] = round(b["main"] + reward, 4)
            b["lifetime_watch_ads"] = int(b.get("lifetime_watch_ads", 0)) + 1
        else:
            b["pending"] = round(b["pending"] + reward, 4)
        b["today_ads"] += 1; b["total_ads"] += 1; b[t + "_today"] += 1
        if t == "auto": b["cfill"] = int(b.get("cfill", 0)) + 1   # ONLY Auto-loop ads fill the yellow Confirm bar (watch ads go straight to main)
        # Lifetime counters тАФ these NEVER reset (even when admin clicks "Reset All Users Ads")
        b["lifetime_earned"] = round(float(b.get("lifetime_earned", 0)) + reward, 4)
        b["lifetime_ads"] = int(b.get("lifetime_ads", 0)) + 1
        pct = float(s.get("ref_bonus", 0) or 0); rid = rec.get("ref")
        if rid and pct > 0:
            rr = d["users"].get(str(rid))
            if rr and not rr.get("banned") and "bal" in rr:
                bonus = round(reward * pct / 100.0, 4)
                rr["bal"]["main"] = round(rr["bal"]["main"] + bonus, 4); rr["ref_earned"] = round(rr.get("ref_earned", 0) + bonus, 4)
        save(d)
        return jsonify(ok=True, state=state(rec), reward=reward, to_main=(t == "watch"), special=is_special)

@app.route('/api/confirm', methods=['POST'])
def api_confirm():
    u = tg_user()
    if not u: return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); rec = ensure_user(d, u)
        if rec.get("banned"): return jsonify(error="banned")
        # Direct confirm is disabled: balance can only move to MAIN through the confirm-ads flow (/api/ad/start + /api/ad/claim, type="confirm")
        return jsonify(error="useads")

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
        usdt = None; cost = amount          # cost = how many TK are taken from the balance
        if method == "binance":             # amount is typed in USDT -> convert to TK with the admin rate
            rate = float(s.get("usdt_rate", 0) or 0)
            if rate <= 0: return jsonify(error="bad data")
            usdt = amount; cost = round(amount * rate, 2)
        if amount < s["min"][method]: return jsonify(error="min", min=s["min"][method], method=method)
        if cost > bl["main"] + 1e-9: return jsonify(error="balance", main=round(bl["main"], 2), need=cost)
        bl["main"] = round(bl["main"] - cost, 4)
        w = {"id": int(time.time() * 1000), "uid": u["id"], "name": uname(u), "username": u.get("username", ""), "method": method, "number": number,
             "amount": cost, "bal": round(bl["main"], 2), "status": "Pending", "date": int(time.time())}
        if usdt is not None: w["usdt"] = usdt
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
        w = None
        for x in d["withdraws"]:
            if x["id"] == b.get("id"):
                if x["status"] != "Pending": return jsonify(error="locked")  # once approved/rejected it can never change again
                x["status"] = b["status"]  # no refund on reject
                w = x
        save(d)
    # Send Telegram notification to the user (only on approve/reject, not on initial request)
    if w and BOT_TOKEN:
        try:
            import urllib.request, urllib.parse
            status_txt = "тЬЕ Withdrawal Approved!" if w["status"] == "Approved" else "тЭМ Withdrawal Rejected!"
            color_emoji = "тЬЕ" if w["status"] == "Approved" else "тЭМ"
            msg = (f"{color_emoji} *Withdrawal {w['status']}!*\n\n"
                   f"ЁЯТ░ Amount: *{(str(w['usdt']) + ' USDT (' + str(w['amount']) + ' TK)') if w.get('usdt') else (str(w['amount']) + ' TK')}*\n"
                   f"ЁЯПж Method: *{w['method'].upper()}*\n"
                   f"ЁЯУ▒ Number: `{w['number']}`\n")
            if w["status"] == "Approved":
                msg += "\nЁЯОЙ ржЖржкржирж╛рж░ withdraw request approve ржХрж░рж╛ рж╣ржпрж╝рзЗржЫрзЗред"
            else:
                msg += "\nтЪая╕П ржЖржкржирж╛рж░ withdraw request reject ржХрж░рж╛ рж╣ржпрж╝рзЗржЫрзЗред ржкрзНрж░ржпрж╝рзЛржЬржирзЗ admin ржПрж░ рж╕рж╛ржерзЗ ржпрзЛржЧрж╛ржпрзЛржЧ ржХрж░рзБржиред"
            payload = urllib.parse.urlencode({
                "chat_id": w["uid"],
                "text": msg,
                "parse_mode": "Markdown",
            }).encode("utf-8")
            req = urllib.request.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload, method="POST")
            urllib.request.urlopen(req, timeout=5).read()
        except Exception:
            pass  # notification failure shouldn't fail the API call
    return jsonify(ok=True)

@app.route('/api/admin/withdraw_delete', methods=['POST'])
def api_admin_wdelete():
    """Permanently delete a single withdraw record by id (admin only). Record cannot come back."""
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    b = request.get_json(force=True) or {}
    try: wid = int(b.get("id"))
    except Exception: return jsonify(error="bad data"), 400
    with _lock:
        d = load()
        before = len(d["withdraws"])
        d["withdraws"] = [x for x in d["withdraws"] if x["id"] != wid]
        after = len(d["withdraws"])
        save(d)
    return jsonify(ok=True, deleted=(before - after))

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
    """Resets every user's DAILY/TOTAL ad counters (today_ads, total_ads, watch_today, auto_today) to 0.
    Does NOT touch lifetime_earned / lifetime_ads (those are permanent on profile page)."""
    if not is_admin(tg_user()): return jsonify(error="forbidden"), 403
    with _lock:
        d = load(); cnt = 0
        for rec in d["users"].values():
            if "bal" in rec:
                b = rec["bal"]
                b["today_ads"] = 0; b["total_ads"] = 0
                b["watch_today"] = 0; b["auto_today"] = 0
                b["day"] = today_key()
                # lifetime_earned and lifetime_ads are intentionally NOT reset
                cnt += 1
            rec.pop("ad", None)
        save(d)
    return jsonify(ok=True, users_reset=cnt)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
