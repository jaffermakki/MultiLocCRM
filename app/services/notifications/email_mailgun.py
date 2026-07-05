"""Mailgun provider, using their HTTP API.

Required environment variables:
    MAILGUN_API_KEY     from Mailgun dashboard > Settings > API Keys
    MAILGUN_DOMAIN      your sending domain, e.g. mg.yourshop.com
    MAILGUN_REGION      optional, "us" (default) or "eu" - must match the region
                        your Mailgun domain was created in
"""
import os
import requests

from app.services.notifications.base import EmailProvider, ProviderNotConfiguredError, NotificationError

REGION_URLS = {
    "us": "https://api.mailgun.net/v3",
    "eu": "https://api.eu.mailgun.net/v3",
}


class MailgunProvider(EmailProvider):
    def __init__(self):
        self.api_key = os.environ.get("MAILGUN_API_KEY", "")
        self.domain = os.environ.get("MAILGUN_DOMAIN", "")
        self.region = os.environ.get("MAILGUN_REGION", "us").lower()

        if not self.api_key or not self.domain:
            raise ProviderNotConfiguredError(
                "Mailgun is not configured. Set MAILGUN_API_KEY and MAILGUN_DOMAIN in .env"
            )

    def send(self, *, to_email, to_name, subject, html_body, text_body=""):
        from_email = os.environ.get("EMAIL_FROM_ADDRESS", "") or f"noreply@{self.domain}"
        from_name = os.environ.get("EMAIL_FROM_NAME", "")
        base_url = REGION_URLS.get(self.region, REGION_URLS["us"])

        data = {
            "from": f"{from_name} <{from_email}>" if from_name else from_email,
            "to": f"{to_name} <{to_email}>" if to_name else to_email,
            "subject": subject,
            "html": html_body,
        }
        if text_body:
            data["text"] = text_body

        try:
            resp = requests.post(
                f"{base_url}/{self.domain}/messages",
                auth=("api", self.api_key),
                data=data,
                timeout=15,
            )
        except requests.RequestException as exc:
            raise NotificationError(f"Mailgun request failed: {exc}") from exc

        if resp.status_code != 200:
            raise NotificationError(f"Mailgun returned {resp.status_code}: {resp.text[:300]}")
