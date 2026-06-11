import os
from email.message import EmailMessage
import smtplib
from celery import Celery

app = Celery("email_tasks", broker="redis://localhost:6379/0")


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email(self, subject: str, body: str, receiver_email: str):
    smtp_server = "://gmail.com"
    smtp_port = 587
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
    except Exception as exc:
        raise self.retry(exc=exc)
