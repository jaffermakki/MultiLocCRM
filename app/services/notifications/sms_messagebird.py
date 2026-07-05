"""MessageBird provider, using their HTTP API.

Required environment variables:
    MESSAGEBIRD_API_KEY
    MESSAGEBIRD_FROM_NUMBER     sender ID - phone number or approved alphanumeric originator
"""
import os
import requests

from app.services.notifications.base import SMSProvider, ProviderNotConfiguredError, NotificationError

API_URL = "https://rest.messagebird.com/messages"


class MessageBirdProvider(SMSProvider):
    def __init__(self):
        self.api_key = os.environ.get("MESSAGEBIRD_API_KEY", "")
        self.from_number = os.environ.get("MESSAGEBIRD_FROM_NUMBER", "")

        if not self.api_key or not self.from_number:
            raise ProviderNotConfiguredError(
                "MessageBird is not configured. Set MESSAGEBIRD_API_KEY and "
                "MESSAGEBIRD_FROM_NUMBER in .env"
            )

    def send(self, *, to_number, body):
        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"AccessKey {self.api_key}"},
                data={"originator": self.from_number, "recipients": to_number, "body": body},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise NotificationError(f"MessageBird request failed: {exc}") from exc

        if resp.status_code not in (200, 201):
            raise NotificationError(f"MessageBird returned {resp.status_code}: {resp.text[:300]}")
