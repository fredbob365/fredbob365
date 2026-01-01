import requests
from bs4 import BeautifulSoup
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

URL = "http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=365&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=1000&vh=&ocl=&och=&sic1=-1&sicl=1000&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=1000&page=1"

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(trades):
    msg = EmailMessage()
    msg["Subject"] = f"Insider Purchases Filed in Last 7 Days ({len(trades)})"
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

        if cols[6].lower() != "purchase":
            continue

        trades.append({
            "filed": cols[1],
            "ticker": cols[3],
            "company": cols[4],
            "insider": cols[5],
            "value": cols[11],
        })

    return trades


def main():
    trades = fetch_trades()
    one_week_ago = datetime.now() - timedelta(days=7)

    last_week_trades = []
    for t in trades:
        try:
            filed_date = datetime.strptime(t["filed"], "%m/%d/%Y")
            if filed_date >= one_week_ago:
                last_week_trades.append(t)
        except ValueError:
            continue

    if last_week_trades:
        send_email(last_week_trades)
        print(f"Emailed {len(last_week_trades)} trades.")
    else:
        print("No trades filed in the last 7 days.")


if __name__ == "__main__":
    main()
