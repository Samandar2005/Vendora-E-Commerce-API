import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.celery_app import celery_app
from app.core.config import get_settings
from celery import shared_task

settings = get_settings()

@shared_task(name="send_payment_success_email")  # <--- name="send_payment_success_email" qo'shing
def send_payment_success_email_task(user_email: str, order_id: str, amount: str, currency: str):
    print(f"📧 Email yuborilmoqda: {user_email}")
    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_USER
    msg["To"] = user_email
    msg["Subject"] = f"Buyurtma #{order_id} uchun to'lov qabul qilindi!"

    body = f"""
    Salom!

    Sizning #{order_id} raqamli buyurtmangiz uchun {amount} {currency.upper()} to'lov muvaffaqiyatli qabul qilindi.

    Xaridingiz uchun tashakkur!
    """
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return f"Email sent to {user_email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

@shared_task(name="send_refund_success_email")
def send_refund_success_email_task(user_email: str, order_id: str, amount: str, currency: str):
    """Mijozga pul muvaffaqiyatli qaytarilgani haqida email yuborish."""
    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_USER
    msg["To"] = user_email
    msg["Subject"] = f"Buyurtma #{order_id} bo'yicha to'lov qaytarildi (Refund)"

    body = f"""
    Salom!

    Sizning #{order_id} raqamli buyurtmangiz uchun {amount} {currency.upper()} miqdoridagi to'lov muvaffaqiyatli qaytarildi.

    Mablag' kartangizga bank shartlariga ko'ra 3-5 ish kuni ichida kelib tushadi.

    Savollaringiz bo'lsa, qo'llab-quvvatlash xizmati bilan bog'lanishingiz mumkin.
    """
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return f"Refund email sent to {user_email}"
    except Exception as e:
        return f"Failed to send refund email: {str(e)}"