import requests
import json
import os
import re
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

URL = "https://www.quiverquant.com/congresstrading/"

SEEN_FILE = "seen_congress_trades.json"

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

MIN_VALUE = 50000  # Minimum trade value to include


def load_seen():
    try:
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def send_email(trades):
    msg = EmailMessage()
    msg["Subject"] = f"New Congressional Trades ≥ ${MIN_VALUE:,} ({len(trades)})"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    body = ""
    for t in trades:
        body += (
            f"{t['name']} ({t['party']} - {t['state']})\n"
            f"Ticker: {t['ticker']}\n"
            f"Transaction: {t['transaction']}\n"
            f"Amount: {t['amount']}\n"
            f"Filed: {t['filed']}\n\n"
        )

    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)


def fetch_trades():
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()

    # Extract the embedded JSON from the page
    match = re.search(r"window\.__NUXT__\s*=\s*(\{.*?\});", r.text, re.S)
    if not match:
        raise RuntimeError("Could not find embedded data on QuiverQuant congress trading page")

    data = json.loads(match.group(1))

    # Find the "trades" section in the Nuxt state tree
    raw_trades = None
    for v in data["state"].values():
        if isinstance(v, dict) and "trades" in v:
            raw_trades = v["trades"]
            break

    if raw_trades is None:
        raise RuntimeError("Trade data not found in embedded JSON")

    trades = []
    for t in raw_trades:
        # Check for amount format like "$50,001 - $100,000"
        amt_str = t.get("amount", "")
        if not amt_str:
            continue

        # Parse the low end of the range
        try:
            low = int(amt_str.replace("$", "").replace(",", "").split("-")[0].strip())
        except Exception:
            continue

        if low < MIN_VALUE:
            continue

        trade_id = f"{t['name']}|{t['ticker']}|{t['filed']}|{t['transaction']}"
        trades.append({
            "id": trade_id,
            "name": t.get("name", ""),
            "party": t.get("party", ""),
            "state": t.get("state", ""),
            "ticker": t.get("ticker", ""),
            "transaction": t.get("transaction", ""),
            "amount": amt_str,
            "filed": t.get("filed", ""),
        })

    return trades


def main():
    seen = load_seen()
    all_trades = fetch_trades()

    one_week_ago = datetime.now() - timedelta(days=7)

    # Filter for last 7 days
    recent = []
    for t in all_trades:
        try:
            filed_dt = datetime.strptime(t["filed"], "%Y-%m-%d")
            if filed_dt >= one_week_ago:
                recent.append(t)
        except ValueError:
            continue

    new_trades = [t for t in recent if t["id"] not in seen]

    if new_trades:
        # Email all last week trades (not only the new ones)
        send_email(recent)

        for t in new_trades:
            seen.add(t["id"])
        save_seen(seen)

        print(
            f"New congress trade detected. Emailed {len(recent)} trades "
            f"({len(new_trades)} new)."
        )
    else:
        print("No new congress trades.")


if __name__ == "__main__":
    main()
