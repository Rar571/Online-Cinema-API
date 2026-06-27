import os
from email.message import EmailMessage
import smtplib
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select, create_engine
from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from models.users import ActivationTokenModel

app = Celery("tasks", broker=f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379/0")

POSTGRESQL_DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('POSTGRES_USERNAME', 'postgres')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOST', 'postgres')}:"
    f"{os.getenv('POSTGRES_DB_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'postgres')}"
)

engine = create_engine(POSTGRESQL_DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email(self, subject: str, body: str, receiver_email: str):
    smtp_server = "smtp.gmail.com"
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


@app.task()
def delete_expired_activation_tokens():
    db = SessionLocal()
    result = db.execute(
        select(ActivationTokenModel).where(
            ActivationTokenModel.expires_at < datetime.now(timezone.utc)
        )
    )
    activation_tokens = result.scalars().all()
    try:
        if activation_tokens:
            for token in activation_tokens:
                db.delete(token)
            db.commit()
    finally:
        db.close()


app.conf.beat_schedule = {
    "clear_expired_activation_tokens": {
        "task": "celery.delete_expired_activation_tokens",
        "schedule": crontab(hour=14, minute=0),
    }
}
