"""
Cronjobs  \u2014  daily 6:00 AM (Bangladesh time) job for Auto Taka Machine.

What it does every morning at 6:00 AM, ONLY if the bot is running:
  1) takes the "Next Day" limits you saved in Admin Panel > Add Limit and makes them today's limits
     (if you left them blank, today's limits stay as they are)
  2) sends the "GOOD MORNING + today's Ad Limit" message to every user (with a New Start button)

If the bot is stopped (/stopbot or /parmanetbotoff) at 6:00 AM -> nothing is sent and no limit changes.
Starting the bot later (9 AM, 11 AM ...) does NOT send the message, because the cron only fires at 6:00.

How to run it: make a free job on cron-job.org (or any cron service) that opens this URL every day at 6:00 AM
(timezone Asia/Dhaka):
        https://YOUR-DOMAIN/cronjobs?key=YOUR_CRON_KEY
Set the same YOUR_CRON_KEY as an environment variable named CRON_KEY on your hosting.
The job runs only once per day, so calling it twice is safe. For a manual test add &force=1 (sends right now).
"""
import os, datetime

BD = datetime.timezone(datetime.timedelta(hours=6))   # Bangladesh time (UTC+6)

def bd_now():
    return datetime.datetime.now(BD)

def morning_message(limit_watch, limit_auto):
    return ("\U0001f48e \U0001f305 <b>\u09b6\u09c1\u09ad \u09b8\u0995\u09be\u09b2</b> \U0001f4b0\n\n"
            "\U0001f305 <b>\u09b6\u09c1\u09ad \u09b8\u0995\u09be\u09b2, AUTO TAKA MACHINE \u09aa\u09b0\u09bf\u09ac\u09be\u09b0!</b>\n\n"
            "\U0001f31e \u09a8\u09a4\u09c1\u09a8 \u09a6\u09bf\u09a8\u09c7\u09b0 \u0995\u09be\u099c \u09b6\u09c1\u09b0\u09c1 \u0995\u09b0\u09c1\u09a8!\n\n"
            "\U0001f514 <b>\u0986\u099c\u0995\u09c7\u09b0 Ad Limit</b> \U0001f514\n"
            "\U0001f48e Watch Ads - <b>" + str(limit_watch) + "</b> \U0001f680\n"
            "\u26a1 Auto Ads - <b>" + str(limit_auto) + "</b> \u2705\n\n"
            "\U0001f4b0 \u09a8\u09bf\u09af\u09bc\u09ae \u09ae\u09c7\u09a8\u09c7 \u0995\u09be\u099c \u0995\u09b0\u09c1\u09a8, \u09ac\u09c7\u09b6\u09bf \u0987\u09a8\u0995\u09be\u09ae \u0995\u09b0\u09c1\u09a8!\n\n"
            "\U0001f447 \u09a8\u09bf\u099a\u09c7 Start \u09ac\u09be\u099f\u09a8\u09c7 \u0995\u09cd\u09b2\u09bf\u0995 \u0995\u09b0\u09c7 \u0995\u09be\u099c \u09b6\u09c1\u09b0\u09c1 \u0995\u09b0\u09c1\u09a8! \U0001f447")

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
    now = bd_now(); today = now.strftime("%Y-%m-%d")
    if not force and now.hour != 6:
        return "skipped: it is not 6 AM (Bangladesh time) now (" + now.strftime("%H:%M") + ")"
    with mod._lock:
        d = mod.load(); s = mod.settings_of(d)
        if s.get("bot_stopped") or s.get("bot_perm_off"):
            return "skipped: bot is OFF, so no message and no limit change"
        if s.get("morning_done") == today and not force:
            return "skipped: today's morning job is already done"
        nw, na = s.get("next_limit_watch"), s.get("next_limit_auto")
        if nw is not None: s["limit_watch"] = int(nw)
        if na is not None: s["limit_auto"] = int(na)
        s["next_limit_watch"] = None; s["next_limit_auto"] = None
        if not force: s["morning_done"] = today      # a manual test (force) must not block the real 6 AM run
        mod.save(d)
        lw, la = s["limit_watch"], s["limit_auto"]
    uname = _bot_username(mod)
    btn = ("\U0001f680 New Start", "https://t.me/" + uname + "?start=morning") if uname else None
    started = mod.start_broadcast(morning_message(lw, la), button=btn, report_to=mod.ADMIN_ID, label="GOOD MORNING \u09ae\u09c7\u09b8\u09c7\u099c")
    if not started:
        with mod._lock:
            d = mod.load(); mod.settings_of(d)["morning_done"] = ""; mod.save(d)
        return "limits applied (watch " + str(lw) + ", auto " + str(la) + ") but another broadcast was running - call again in a minute"
    return "OK: limits watch=" + str(lw) + " auto=" + str(la) + ", good morning message started"

def handle(request, mod):
    key = os.getenv("CRON_KEY", "")
    if key and request.args.get("key", "") != key:
        return "forbidden", 403
    force = request.args.get("force") == "1"
    if force and not key:
        return "force needs CRON_KEY to be set on the server", 403
    return run_morning(mod, force=force), 200
