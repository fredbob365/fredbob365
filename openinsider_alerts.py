import requests
from bs4 import BeautifulSoup
import os
import smtplib
from email.message import EmailMessage

URL = "http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=7&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=1000&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=1000&page=1"

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def fetch_trades():
    response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table", class_="tinytable")
    rows = table.find_all("tr")[1:]

    trades = []
    for row in rows:
        cols = [c.text.strip() for c in row.find_all("td")]

        trades.append({
            "filed": cols[1],
            "ticker": cols[3],
            "company": cols[4],
            "insider": cols[5],
            "trade_type": cols[6],
            "price": cols[8],
            "quantity": cols[9],
            "value": cols[11],
        })

    return trades


def send_email(trades):
    msg = EmailMessage()
    msg["Subject"] = f"OpenInsider – Last 7 Days ({len(trades)} trades)"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    body = ""
    for t in trades:
        body += (
            f"{t['ticker']} | {t['company']}\n"
            f"Insider: {t['insider']}\n"
            f"Type: {t['trade_type']}\n"
            f"Value: {t['value']}\n"
            f"Filed: {t['filed']}\n"
            f"{'-'*40}\n"
        )

    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)


def main():
    trades = fetch_trades()

    if trades:
        send_email(trades)
        print(f"Emailed {len(trades)} trades.")
    else:
        print("No trades found.")


if __name__ == "__main__":
    main()
