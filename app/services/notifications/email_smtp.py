"""Generic SMTP provider - works with Gmail, Outlook/Office365, Zoho Mail, your own
mail server, or literally any provider that speaks SMTP. This is the universal
fallback: if a specific provider class doesn't exist yet for whoever you use, SMTP
almost certainly still works, since virtually every email service offers an SMTP
relay even if they'd prefer you use their API.

Required environment variables:
    SMTP_HOST       e.g. smtp.gmail.com
    SMTP_PORT       e.g. 587 (TLS) or 465 (SSL)
    SMTP_USER       login username (often your full email address)
    SMTP_PASSWORD   login password (for Gmail/Outlook, this usually needs to be an
                    "app password", not your normal account password, due to their
                    security policies - each provider's help docs cover this)
    SMTP_USE_SSL    optional, "true" to use implicit SSL on connect (port 465 style)
                    instead of STARTTLS (port 587 style, the default)
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.notifications.base import EmailProvider, ProviderNotConfiguredError, NotificationError


class SMTPProvider(EmailProvider):
    def __init__(self):
        self.host = os.environ.get("SMTP_HOST", "")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.use_ssl = os.environ.get("SMTP_USE_SSL", "false").lower() == "true"

        if not self.host or not self.user or not self.password:
            raise ProviderNotConfiguredError(
                "SMTP is not configured. Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in .env"
            )

    def send(self, *, to_email, to_name, subject, html_body, text_body=""):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.user
        msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=15)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=15)
                server.starttls()

            server.login(self.user, self.password)
            server.sendmail(self.user, [to_email], msg.as_string())
            server.quit()
        except smtplib.SMTPException as exc:
            raise NotificationError(f"SMTP send failed: {exc}") from exc
        except OSError as exc:
            raise NotificationError(f"Could not connect to SMTP server {self.host}:{self.port}: {exc}") from exc
