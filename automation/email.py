from __future__ import annotations

import smtplib
from email.message import EmailMessage
from os import getenv

from automation.models import Ticket


def send_email_notification(pr_url: str, ticket: Ticket) -> None:
    host = getenv("SMTP_HOST")
    try:
        port = int(getenv("SMTP_PORT", "587"))
    except ValueError as exc:
        raise ValueError("SMTP_PORT must be a valid integer") from exc
    username = getenv("SMTP_USERNAME")
    password = getenv("SMTP_PASSWORD")
    sender = getenv("EMAIL_SENDER")
    recipient = getenv("EMAIL_RECIPIENT")
    if not all([host, username, password, sender, recipient]):
        return

    msg = EmailMessage()
    msg["Subject"] = f"PR ready for review: {ticket.title}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(f"Ticket {ticket.id} now has a pull request ready:\n{pr_url}")

    try:
        with smtplib.SMTP(host, port) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError):
        return
