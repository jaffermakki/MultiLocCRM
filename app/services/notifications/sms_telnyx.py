"""Telnyx provider, using their HTTP API.

Required environment variables:
    TELNYX_API_KEY
    TELNYX_FROM_NUMBER          your Telnyx phone number, e.g. +14165551234
    TELNYX_MESSAGING_PROFILE_ID  optional - required by some Telnyx account
                                 configurations; leave blank if not needed
"""
import os
import requests

from app.services.notifications.base import SMSProvider, ProviderNotConfiguredError, NotificationError

API_URL = "https://api.telnyx.com/v2/messages"


class TelnyxProvider(SMSProvider):
    def __init__(self):
        self.api_key = os.environ.get("TELNYX_API_KEY", "")
        self.from_number = os.environ.get("TELNYX_FROM_NUMBER", "")
        self.messaging_profile_id = os.environ.get("TELNYX_MESSAGING_PROFILE_ID", "")

        if not self.api_key or not self.from_number:
            raise ProviderNotConfiguredError(
                "Telnyx is not configured. Set TELNYX_API_KEY and TELNYX_FROM_NUMBER in .env"
            )

    def send(self, *, to_number, body):
        payload = {"from": self.from_number, "to": to_number, "text": body}
        if self.messaging_profile_id:
            payload["messaging_profile_id"] = self.messaging_profile_id

        try:
            resp = requests.post(
                API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise NotificationError(f"Telnyx request failed: {exc}") from exc

        if resp.status_code not in (200, 201, 202):
            raise NotificationError(f"Telnyx returned {resp.status_code}: {resp.text[:300]}")
