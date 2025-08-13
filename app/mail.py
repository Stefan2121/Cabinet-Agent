import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

from .models import Appointment
from . import db


def send_email(to_email: str, subject: str, body: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    sender_email = os.getenv("SENDER_EMAIL", smtp_user or "no-reply@example.com")
    sender_name = os.getenv("SENDER_NAME", "Cabinet Stomatologic")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = to_email

    # Dev fallback: if SMTP creds not provided, just print the email
    if not smtp_host or not smtp_user or not smtp_pass:
        print(f"[DEV] Email către {to_email}: {subject}\n{body}\n")
        return True

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"Eroare trimitere email către {to_email}: {e}")
        return False


def send_appointment_reminder_emails():
    tz_name = os.getenv("APP_TIMEZONE", "Europe/Bucharest")
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz).replace(tzinfo=None)  # store naive local times in DB

    # Look for appointments roughly 48h from now (±1h window)
    low = now + timedelta(hours=47)
    high = now + timedelta(hours=49)

    appointments = (
        Appointment.query.filter(
            Appointment.start_at >= low,
            Appointment.start_at <= high,
            Appointment.reminder_sent.is_(False),
        ).all()
    )

    count = 0
    for appt in appointments:
        if not appt.patient or not appt.patient.email:
            continue

        date_str = appt.start_at.strftime("%d.%m.%Y")
        time_str = appt.start_at.strftime("%H:%M")
        subject = "Reminder programare la cabinet (în 2 zile)"
        body = (
            f"Bună, {appt.patient.full_name},\n\n"
            f"Vă reamintim că aveți o programare la cabinet peste 2 zile,\n"
            f"în data de {date_str} la ora {time_str}.\n\n"
            f"Dacă doriți reprogramare sau aveți întrebări, vă rugăm să ne contactați.\n\n"
            f"Vă așteptăm,\n"
            f"{os.getenv('SENDER_NAME', 'Cabinet Stomatologic')}"
        )

        if send_email(appt.patient.email, subject, body):
            appt.reminder_sent = True
            count += 1

    if count > 0:
        db.session.commit()

    return count