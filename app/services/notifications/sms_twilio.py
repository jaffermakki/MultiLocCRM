"""Twilio provider, using their HTTP API directly (no twilio-python SDK needed).

Required environment variables:
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_FROM_NUMBER     your Twilio phone number, e.g. +14165551234
"""
import os
import requests

from app.services.notifications.base import SMSProvider, ProviderNotConfiguredError, NotificationError


class TwilioProvider(SMSProvider):
    def __init__(self):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.environ.get("TWILIO_FROM_NUMBER", "")

        if not self.account_sid or not self.auth_token or not self.from_number:
            raise ProviderNotConfiguredError(
                "Twilio is not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
                "and TWILIO_FROM_NUMBER in .env"
            )

    def send(self, *, to_number, body):
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

        try:
            resp = requests.post(
                url,
                auth=(self.account_sid, self.auth_token),
                data={"From": self.from_number, "To": to_number, "Body": body},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise NotificationError(f"Twilio request failed: {exc}") from exc

        if resp.status_code not in (200, 201):
            raise NotificationError(f"Twilio returned {resp.status_code}: {resp.text[:300]}")
