"""Vonage (formerly Nexmo) provider, using their HTTP API.

Required environment variables:
    VONAGE_API_KEY
    VONAGE_API_SECRET
    VONAGE_FROM_NUMBER     sender ID - either a phone number or an approved
                          alphanumeric sender name like "TechProRepairs", depending
                          on what your account/region supports
"""
import os
import requests

from app.services.notifications.base import SMSProvider, ProviderNotConfiguredError, NotificationError

API_URL = "https://rest.nexmo.com/sms/json"


class VonageProvider(SMSProvider):
    def __init__(self):
        self.api_key = os.environ.get("VONAGE_API_KEY", "")
        self.api_secret = os.environ.get("VONAGE_API_SECRET", "")
        self.from_number = os.environ.get("VONAGE_FROM_NUMBER", "")

        if not self.api_key or not self.api_secret or not self.from_number:
            raise ProviderNotConfiguredError(
                "Vonage is not configured. Set VONAGE_API_KEY, VONAGE_API_SECRET, "
                "and VONAGE_FROM_NUMBER in .env"
            )

    def send(self, *, to_number, body):
        # Vonage wants numbers without a leading "+"
        clean_to = to_number.lstrip("+")

        try:
            resp = requests.post(
                API_URL,
                data={
                    "api_key": self.api_key,
                    "api_secret": self.api_secret,
                    "from": self.from_number,
                    "to": clean_to,
                    "text": body,
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            raise NotificationError(f"Vonage request failed: {exc}") from exc

        if resp.status_code != 200:
            raise NotificationError(f"Vonage returned {resp.status_code}: {resp.text[:300]}")

        # Vonage returns 200 even on per-message failures - the real status is inside
        # the JSON body, so it needs checking explicitly rather than trusting the
        # HTTP status code alone.
        try:
            result = resp.json()
            messages = result.get("messages", [{}])
            if messages and messages[0].get("status") != "0":
                error_text = messages[0].get("error-text", "Unknown error")
                raise NotificationError(f"Vonage rejected the message: {error_text}")
        except ValueError:
            raise NotificationError(f"Vonage returned an unexpected response: {resp.text[:300]}")
