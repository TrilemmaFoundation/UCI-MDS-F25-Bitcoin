import smtplib
import ssl
from email.message import EmailMessage
import os

# Define email sender and receiver
email_sender = "bitcoin.accumulation.updates@gmail.com"
email_password = os.getenv("BTC_CAPSTONE_EMAIL_PASSWORD", "")


def send_email(subject: str, body: str, email_recipient: str):
    # Create email message
    em = EmailMessage()
    em["From"] = "Bitcoin Daily Purchase"
    em["To"] = email_recipient
    em["Subject"] = subject

    em.add_alternative(body, subtype="html")

    # Add SSL (layer of security)
    context = ssl.create_default_context()

    # Log in and send the email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        response = smtp.sendmail(email_sender, email_recipient, em.as_string())
        if not response:
            print(f"Successfully sent email to {email_recipient}")
        else:
            print(f"Failed to send email. Server response: {response}")


# send_email(
#     subject="Daily Allotment",
#     body="ayo ayo ayo 123",
#     email_recipient="smaueltown@gmail.com",
# )
