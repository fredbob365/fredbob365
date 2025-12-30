import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

URL = "http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=365&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=10000&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=1000&page=1"

SEEN_FILE = "seen_trades.json"

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


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
    msg["Subject"] = f"New $10M+ Insider Purchase ({len(trades)})"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    body = ""
    for t in trades:
        body += (
            f"{t['ticker']} | {t['company']}\n"
            f"Insider: {t['insider']}\n"
            f"Value: {t['value']}\n"
            f"Filed: {t['filed']}\n\n"
        )

    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)


def fetch_trades():
    response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table", {"class": "tinytable"})
    rows = table.find_all("tr")[1:]

    trades = []
    for row in rows:
        cols = [c.text.strip() for c in row.find_all("td")]
        trade_id = "|".join(cols[:6])

        trades.append({
            "id": trade_id,
            "filed": cols[1],  # filed date as string
            "ticker": cols[3],
            "company": cols[4],
            "insider": cols[5],
            "value": cols[11]
        })

    return trades


def main():
    seen = load_seen()
    trades = fetch_trades()

    # Filter trades to the past 7 days
    one_week_ago = datetime.now() - timedelta(days=7)
    recent_trades = []
    for t in trades:
        try:
            trade_date = datetime.strptime(t["filed"], "%m/%d/%Y")
            if trade_date >= one_week_ago:
                recent_trades.append(t)
        except ValueError:
            # Skip trades with invalid dates
            continue

    # Only include trades not seen before
    new_trades = [t for t in recent_trades if t["id"] not in seen]

    if new_trades:
        send_email(new_trades)
        for t in new_trades:
            seen.add(t["id"])
        save_seen(seen)
        print(f"Emailed {len(new_trades)} new trade(s).")
    else:
        print("No new trades.")


if __name__ == "__main__":
    main()
