"""Postmark provider, using their HTTP API.

Required environment variables:
    POSTMARK_SERVER_TOKEN   from Postmark dashboard > Servers > [your server] > API Tokens
"""
import os
import requests

from app.services.notifications.base import EmailProvider, ProviderNotConfiguredError, NotificationError

API_URL = "https://api.postmarkapp.com/email"


class PostmarkProvider(EmailProvider):
    def __init__(self):
        self.token = os.environ.get("POSTMARK_SERVER_TOKEN", "")
        if not self.token:
            raise ProviderNotConfiguredError("Postmark is not configured. Set POSTMARK_SERVER_TOKEN in .env")

    def send(self, *, to_email, to_name, subject, html_body, text_body=""):
        from_email = os.environ.get("EMAIL_FROM_ADDRESS", "")
        from_name = os.environ.get("EMAIL_FROM_NAME", "")
        if not from_email:
            raise ProviderNotConfiguredError("Set EMAIL_FROM_ADDRESS in .env (must be a verified Sender Signature in Postmark)")

        payload = {
            "From": f"{from_name} <{from_email}>" if from_name else from_email,
            "To": f"{to_name} <{to_email}>" if to_name else to_email,
            "Subject": subject,
            "HtmlBody": html_body,
        }
        if text_body:
            payload["TextBody"] = text_body

        try:
            resp = requests.post(
                API_URL,
                json=payload,
                headers={
                    "X-Postmark-Server-Token": self.token,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            raise NotificationError(f"Postmark request failed: {exc}") from exc

        if resp.status_code != 200:
            raise NotificationError(f"Postmark returned {resp.status_code}: {resp.text[:300]}")
