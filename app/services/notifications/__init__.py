"""Factory + high-level send functions. This is the only module the rest of the app
should import from - blueprints/services elsewhere call send_receipt_email() or
send_repair_ready_sms(), never a specific provider class directly. Which provider
actually runs is decided here, based on ShopSettings.email_provider / sms_provider -
so switching providers is a Settings page change, not a code change.

To add a new provider later: write one new class in this package implementing
EmailProvider or SMSProvider (see base.py and any existing provider for the pattern),
then add one line to EMAIL_PROVIDERS or SMS_PROVIDERS below. Nothing else changes.
"""
import logging

from app.models.settings import ShopSettings
from app.services.notifications.base import NotificationError, ProviderNotConfiguredError

logger = logging.getLogger(__name__)

EMAIL_PROVIDERS = {
    "smtp": "app.services.notifications.email_smtp.SMTPProvider",
    "sendgrid": "app.services.notifications.email_sendgrid.SendGridProvider",
    "mailgun": "app.services.notifications.email_mailgun.MailgunProvider",
    "postmark": "app.services.notifications.email_postmark.PostmarkProvider",
    "ses": "app.services.notifications.email_ses.SESProvider",
}

SMS_PROVIDERS = {
    "twilio": "app.services.notifications.sms_twilio.TwilioProvider",
    "vonage": "app.services.notifications.sms_vonage.VonageProvider",
    "messagebird": "app.services.notifications.sms_messagebird.MessageBirdProvider",
    "telnyx": "app.services.notifications.sms_telnyx.TelnyxProvider",
    "aws_sns": "app.services.notifications.sms_sns.SNSProvider",
}

EMAIL_PROVIDER_LABELS = {
    "smtp": "SMTP (Gmail, Outlook, your own mail server, etc.)",
    "sendgrid": "SendGrid",
    "mailgun": "Mailgun",
    "postmark": "Postmark",
    "ses": "Amazon SES",
}

SMS_PROVIDER_LABELS = {
    "twilio": "Twilio",
    "vonage": "Vonage (Nexmo)",
    "messagebird": "MessageBird",
    "telnyx": "Telnyx",
    "aws_sns": "Amazon SNS",
}


def _load_class(dotted_path: str):
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)


def get_email_provider(settings: ShopSettings = None):
    settings = settings or ShopSettings.get()
    key = settings.email_provider or "smtp"
    if key not in EMAIL_PROVIDERS:
        raise ProviderNotConfiguredError(f'Unknown email provider "{key}"')
    return _load_class(EMAIL_PROVIDERS[key])()


def get_sms_provider(settings: ShopSettings = None):
    settings = settings or ShopSettings.get()
    key = settings.sms_provider or "twilio"
    if key not in SMS_PROVIDERS:
        raise ProviderNotConfiguredError(f'Unknown SMS provider "{key}"')
    return _load_class(SMS_PROVIDERS[key])()


def send_receipt_email(invoice, settings: ShopSettings = None) -> bool:
    """Sends a simple HTML receipt email for the given invoice to its customer.
    Returns True on success, False if email isn't enabled/configured or the
    customer has no email address. Raises NotificationError if sending was
    attempted but failed (network error, provider rejected it, etc.) so callers
    can decide whether to surface that to the user or just log it - checkout
    should never fail just because the receipt email didn't send."""
    settings = settings or ShopSettings.get()

    if not settings.email_receipts_enabled:
        return False
    if not invoice.customer or not invoice.customer.email:
        return False

    subject = settings.email_receipt_subject.format(shop_name=settings.shop_name)
    html_body = _render_receipt_html(invoice, settings)

    provider = get_email_provider(settings)
    provider.send(
        to_email=invoice.customer.email,
        to_name=invoice.customer.name,
        subject=subject,
        html_body=html_body,
    )
    logger.info(f"Receipt email sent for {invoice.invoice_number} to {invoice.customer.email}")
    return True


def send_repair_ready_sms(repair, settings: ShopSettings = None) -> bool:
    """Sends the 'ready for pickup' SMS using the configured template. Returns True
    on success, False if SMS isn't enabled/configured or the customer has no phone
    number. Raises NotificationError on a genuine send failure."""
    settings = settings or ShopSettings.get()

    if not settings.sms_enabled:
        return False
    if not repair.customer or not repair.customer.phone:
        return False

    message = settings.sms_ready_template.format(
        customer_name=repair.customer.name,
        device=repair.device,
        shop_name=settings.shop_name,
    )

    provider = get_sms_provider(settings)
    provider.send(to_number=repair.customer.phone, body=message)
    logger.info(f"Ready-for-pickup SMS sent for repair #{repair.ticket_no} to {repair.customer.phone}")
    return True


def _render_receipt_html(invoice, settings: ShopSettings) -> str:
    rows = "".join(
        f"<tr><td style='padding:4px 8px;'>{item.qty}x {item.description}</td>"
        f"<td style='padding:4px 8px; text-align:right;'>{settings.currency}{item.line_total:.2f}</td></tr>"
        for item in invoice.items
    )
    return f"""
    <div style="font-family:sans-serif; max-width:480px; margin:0 auto;">
      <h2 style="margin-bottom:4px;">{settings.shop_name}</h2>
      <p style="color:#666; margin-top:0;">Receipt {invoice.invoice_number}</p>
      <table style="width:100%; border-collapse:collapse;">
        {rows}
      </table>
      <hr>
      <p style="text-align:right; font-size:18px; font-weight:bold;">
        Total: {settings.currency}{float(invoice.total):.2f}
      </p>
      <p style="color:#999; font-size:12px; text-align:center; margin-top:24px;">
        {settings.invoice_footer_note}
      </p>
    </div>
    """
