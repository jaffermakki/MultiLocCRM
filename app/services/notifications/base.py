"""Provider-agnostic interfaces for sending email and SMS.

The pattern here: every concrete provider (SendGrid, Twilio, SMTP, etc.) implements
one of these two interfaces. Application code (notifications.py) never imports a
specific provider directly - it asks the factory functions (get_email_provider() /
get_sms_provider()) for "whatever's configured right now", based on
ShopSettings.email_provider / sms_provider. Adding a new provider later means writing
one new class here and registering it in the factory - nothing else in the app changes.

Credentials (API keys, auth tokens, SMTP passwords) are read from environment
variables inside each provider's __init__, never from the database or passed in as
plain arguments from request data - this keeps secrets out of the DB and out of logs.
"""
from abc import ABC, abstractmethod


class NotificationError(Exception):
    """Raised when a send fails - callers should catch this and decide whether to
    surface it to the user, retry, or just log it, rather than letting a notification
    failure break an unrelated flow like checkout or repair status updates."""
    pass


class ProviderNotConfiguredError(NotificationError):
    """Raised when the selected provider is missing required credentials/config."""
    pass


class EmailProvider(ABC):
    @abstractmethod
    def send(self, *, to_email: str, to_name: str, subject: str, html_body: str, text_body: str = "") -> None:
        """Send an email. Raises NotificationError subclasses on failure."""
        raise NotImplementedError


class SMSProvider(ABC):
    @abstractmethod
    def send(self, *, to_number: str, body: str) -> None:
        """Send an SMS. Raises NotificationError subclasses on failure."""
        raise NotImplementedError
