import json, os, sys, datetime, urllib.request

API_KEY = os.environ["FINNHUB_KEY"]
url = f"https://finnhub.io/api/v1/quote?symbol=BNO&token={API_KEY}"

with urllib.request.urlopen(url) as resp:
    data = json.load(resp)

price = data.get("c")
high = data.get("h")
if not price:
    print("No price returned, exiting")
    sys.exit(1)

today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

with open("history.json") as f:
    history = json.load(f)

if history and history[-1]["d"] == today:
    history[-1]["p"] = round(price, 2)
    if high:
        # keep the highest high seen across runs on the same day
        history[-1]["h"] = round(max(high, history[-1].get("h", 0)), 2)
    print(f"Updated today's entry: {today} = {price}")
else:
    entry = {"d": today, "p": round(price, 2)}
    if high:
        entry["h"] = round(high, 2)
    history.append(entry)
    print(f"Appended new entry: {today} = {price}")

with open("history.json", "w") as f:
    json.dump(history, f, separators=(",", ":"))
