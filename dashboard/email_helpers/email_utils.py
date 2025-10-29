import os
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587  # STARTTLS

EMAIL_SENDER = "bitcoin.accumulation.updates@gmail.com"
EMAIL_PASSWORD = os.getenv(
    "BTC_CAPSTONE_EMAIL_PASSWORD"
)  # set this in your deployment env

if not EMAIL_PASSWORD:
    raise RuntimeError("Missing BTC_CAPSTONE_EMAIL_PASSWORD environment variable")


def send_email(subject: str, body: str, email_recipient: str):
    msg = EmailMessage()
    msg["From"] = f"Bitcoin Daily Purchase <{EMAIL_SENDER}>"
    msg["To"] = email_recipient
    msg["Subject"] = subject
    msg.add_alternative(body, subtype="html")

    # connect using plain SMTP then upgrade with STARTTLS
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        context = ssl.create_default_context()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)


# send_email(
#     subject="Daily Allotment",
#     body="ayo ayo ayo 123",
#     email_recipient="smaueltown@gmail.com",
# )
