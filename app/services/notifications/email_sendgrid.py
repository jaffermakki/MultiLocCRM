"""SendGrid provider, using their HTTP API directly (no sendgrid-python SDK needed,
which keeps the dependency list smaller for people who aren't using SendGrid).

Required environment variables:
    SENDGRID_API_KEY   from SendGrid dashboard > Settings > API Keys
"""
import os
import requests

from app.services.notifications.base import EmailProvider, ProviderNotConfiguredError, NotificationError

API_URL = "https://api.sendgrid.com/v3/mail/send"


class SendGridProvider(EmailProvider):
    def __init__(self):
        self.api_key = os.environ.get("SENDGRID_API_KEY", "")
        if not self.api_key:
            raise ProviderNotConfiguredError("SendGrid is not configured. Set SENDGRID_API_KEY in .env")

    def send(self, *, to_email, to_name, subject, html_body, text_body=""):
        from_email = os.environ.get("EMAIL_FROM_ADDRESS", "")
        from_name = os.environ.get("EMAIL_FROM_NAME", "")
        if not from_email:
            raise ProviderNotConfiguredError("Set EMAIL_FROM_ADDRESS in .env (the verified sender address in SendGrid)")

        content = [{"type": "text/html", "value": html_body}]
        if text_body:
            content.insert(0, {"type": "text/plain", "value": text_body})

        payload = {
            "personalizations": [{"to": [{"email": to_email, "name": to_name or to_email}]}],
            "from": {"email": from_email, "name": from_name or from_email},
            "subject": subject,
            "content": content,
        }

        try:
            resp = requests.post(
                API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise NotificationError(f"SendGrid request failed: {exc}") from exc

        if resp.status_code not in (200, 201, 202):
            raise NotificationError(f"SendGrid returned {resp.status_code}: {resp.text[:300]}")
