"""
Cronjobs — daily bot ON/OFF + ad-limit-reset jobs for Auto Taka Machine (Bangladesh time, Asia/Dhaka).

Two independent jobs run every time this URL is hit:

  1) MORNING (bot ON):  at Admin Panel > Bot Control > "Bot ON Time" (used to be fixed 6:00 AM, now
     admin-editable) it:
       - turns the bot back ON if it was OFF (manual /stopbot, Admin Panel "Stop Now", or the EVENING
         job below) - EXCEPT if it was turned off PERMANENTLY (/parmanetbotoff or Admin Panel "Permanent
         Off"), which only /startbot or the panel's "Start Now" button can undo.
       - takes the "Next Day" ad limits saved in Admin Panel > Add Limit and makes them today's limits
         (left blank = today's limits stay as they are)
       - sends the "GOOD MORNING + today's Ad Limit" message to every user (with a New Start button)

  2) EVENING (bot OFF): only if enabled in Admin Panel > Bot Control, at "Bot OFF Time" it turns the bot
     OFF automatically and sends the usual "bot is under maintenance" notice to every user. It turns back
     ON by itself at the next MORNING job (or any time the admin taps "Start Bot Now").

Each job only runs ONCE per calendar day (Bangladesh date), so hitting this URL many times a day is safe
and is in fact REQUIRED now that the times are admin-editable: make a free job on cron-job.org (or any
cron service) that opens this URL every 5-10 MINUTES, all day, every day (timezone does not matter, the
job itself always works in Asia/Dhaka time):
        https://YOUR-DOMAIN/cronjobs?key=YOUR_CRON_KEY
Set the same YOUR_CRON_KEY as an environment variable named CRON_KEY on your hosting. Whatever time the
admin sets in the panel, the next time this URL is hit after that time, the job fires (so keep the
cron-job.org interval short, 5 minutes is ideal, 10 minutes is fine).

For a manual test: add &force=1 to run the MORNING job right now, or &force_evening=1 for the EVENING
job - both need CRON_KEY set. A forced run does not count as "today's job already done", so the real
scheduled run still happens later the same day.
"""
import os, datetime

BD = datetime.timezone(datetime.timedelta(hours=6))   # Bangladesh time (UTC+6)

def bd_now():
    return datetime.datetime.now(BD)

def _hm(hour, minute, default_h, default_m):
    try: h = int(hour)
    except Exception: h = default_h
    try: m = int(minute)
    except Exception: m = default_m
    return max(0, min(23, h)), max(0, min(59, m))

def _due(now, hour, minute):
    return now.hour * 60 + now.minute >= hour * 60 + minute

def morning_message(limit_watch, limit_auto):
    return ("\U0001f48e \U0001f305 <b>শুভ সকাল</b> \U0001f4b0\n\n"
            "\U0001f305 <b>শুভ সকাল, AUTO TAKA MACHINE পরিবার!</b>\n\n"
            "\U0001f31e নতুন দিনের কাজ শুরু করুন!\n\n"
            "\U0001f514 <b>আজকের Ad Limit</b> \U0001f514\n"
            "\U0001f48e Watch Ads - <b>" + str(limit_watch) + "</b> \U0001f680\n"
            "⚡ Auto Ads - <b>" + str(limit_auto) + "</b> ✅\n\n"
            "\U0001f4b0 নিয়ম মেনে কাজ করুন, বেশি ইনকাম করুন!\n\n"
            "\U0001f447 নিচে Start বাটনে ক্লিক করে কাজ শুরু করুন! \U0001f447")

def _bot_username(mod):
    try:
        import asyncio
        from telegram import Bot
        async def g():
            async with Bot(mod.BOT_TOKEN) as b:
                return (await b.get_me()).username or ""
        return asyncio.run(g())
    except Exception:
        return ""

def run_morning(mod, force=False):
    """Bot ON job. Fires once/day at settings.morning_hour:morning_minute (Bangladesh time)."""
    now = bd_now(); today = now.strftime("%Y-%m-%d")
    with mod._lock:
        d = mod.load(); s = mod.settings_of(d)
        hour, minute = _hm(s.get("morning_hour"), s.get("morning_minute"), 6, 0)
        if not force and not _due(now, hour, minute):
            return "skipped: bot-ON time not reached yet (set %02d:%02d, now %s)" % (hour, minute, now.strftime("%H:%M"))
        if s.get("bot_perm_off"):
            return "skipped: bot is PERMANENTLY off, only /startbot or Admin Panel > Bot Control > Start Now can turn it back on"
        if s.get("morning_done") == today and not force:
            return "skipped: today's bot-ON job is already done"
        nw, na = s.get("next_limit_watch"), s.get("next_limit_auto")
        if nw is not None: s["limit_watch"] = int(nw)
        if na is not None: s["limit_auto"] = int(na)
        s["next_limit_watch"] = None; s["next_limit_auto"] = None
        s["bot_stopped"] = False     # daily bot-ON always clears a stop made manually, by Admin Panel, or by the EVENING job
        if not force: s["morning_done"] = today      # a manual test (force) must not block the real scheduled run
        mod.save(d)
        lw, la = s["limit_watch"], s["limit_auto"]
    uname = _bot_username(mod)
    btn = ("\U0001f680 New Start", "https://t.me/" + uname + "?start=morning") if uname else None
    started = mod.start_broadcast(morning_message(lw, la), button=btn, report_to=mod.ADMIN_ID, label="GOOD MORNING মেসেজ")
    if not started:
        with mod._lock:
            d = mod.load(); mod.settings_of(d)["morning_done"] = ""; mod.save(d)
        return "bot turned ON, limits applied (watch " + str(lw) + ", auto " + str(la) + ") but another broadcast was already running - call again in a minute to send the message"
    return "OK: bot turned ON, limits watch=" + str(lw) + " auto=" + str(la) + ", good morning message started"

def run_evening(mod, force=False):
    """Bot OFF job. Only runs if settings.evening_off_enabled is on. Fires once/day at
    settings.evening_hour:evening_minute (Bangladesh time)."""
    now = bd_now(); today = now.strftime("%Y-%m-%d")
    with mod._lock:
        d = mod.load(); s = mod.settings_of(d)
        if not s.get("evening_off_enabled") and not force:
            return "skipped: scheduled bot-OFF is not enabled in Admin Panel > Bot Control"
        hour, minute = _hm(s.get("evening_hour"), s.get("evening_minute"), 17, 0)
        if not force and not _due(now, hour, minute):
            return "skipped: bot-OFF time not reached yet (set %02d:%02d, now %s)" % (hour, minute, now.strftime("%H:%M"))
        if s.get("bot_perm_off") or s.get("bot_stopped"):
            if not force: s["evening_done"] = today; mod.save(d)
            return "skipped: bot is already off"
        if s.get("evening_done") == today and not force:
            return "skipped: today's bot-OFF job is already done"
        s["bot_stopped"] = True
        if not force: s["evening_done"] = today
        mod.save(d)
    started = mod.start_broadcast(mod.offnow_html(), button=("\U0001f4e2 Official Channel", mod.TG_CHANNEL_URL),
                                   report_to=mod.ADMIN_ID, label="AUTO BOT OFF নোটিশ")
    if not started:
        with mod._lock:
            d = mod.load(); mod.settings_of(d)["evening_done"] = ""; mod.save(d)
        return "bot turned OFF but another broadcast was already running - the notice will not resend automatically, call again in a minute if you need it sent"
    return "OK: bot turned OFF (scheduled), notice sent to everyone"

def handle(request, mod):
    key = os.getenv("CRON_KEY", "")
    if key and request.args.get("key", "") != key:
        return "forbidden", 403
    force = request.args.get("force") == "1"
    force_evening = request.args.get("force_evening") == "1"
    if (force or force_evening) and not key:
        return "force needs CRON_KEY to be set on the server", 403
    r1 = run_morning(mod, force=force)
    r2 = run_evening(mod, force=force_evening)
    return "MORNING (bot ON): " + r1 + "\nEVENING (bot OFF): " + r2, 200
