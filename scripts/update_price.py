import json, os, sys, datetime, urllib.request
from zoneinfo import ZoneInfo

API_KEY = os.environ["FINNHUB_KEY"]
url = f"https://finnhub.io/api/v1/quote?symbol=BNO&token={API_KEY}"

with urllib.request.urlopen(url, timeout=30) as resp:
    data = json.load(resp)

price = data.get("c")
high = data.get("h")
traded_at = data.get("t")
if not price:
    print("No price returned, exiting")
    sys.exit(1)

# Date the entry by the last trade, in New York time. The scheduled run
# often fires hours late, past midnight UTC, so the run-time date would
# label the close with the wrong day (and drop days when two runs collide).
NY = ZoneInfo("America/New_York")
if traded_at:
    day = datetime.datetime.fromtimestamp(traded_at, NY).strftime("%Y-%m-%d")
else:
    day = datetime.datetime.now(NY).strftime("%Y-%m-%d")

with open("history.json") as f:
    history = json.load(f)

last = history[-1]["d"] if history else ""
if last == day:
    history[-1]["p"] = round(price, 2)
    if high:
        # keep the highest high seen across runs on the same day
        history[-1]["h"] = round(max(high, history[-1].get("h", 0)), 2)
    print(f"Updated entry: {day} = {price}")
elif day > last:
    entry = {"d": day, "p": round(price, 2)}
    if high:
        entry["h"] = round(high, 2)
    history.append(entry)
    print(f"Appended new entry: {day} = {price}")
else:
    print(f"Quote is for {day}, older than last entry {last}; nothing to do")
    sys.exit(0)

with open("history.json", "w") as f:
    json.dump(history, f, separators=(",", ":"))
