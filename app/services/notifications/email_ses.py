"""Amazon SES provider, using boto3 (AWS's official SDK). Unlike the other email
providers here, SES genuinely needs boto3 rather than a plain HTTP call - AWS
requires SigV4 request signing, which boto3 handles correctly and which would be
both painful and risky to hand-roll. boto3 is imported lazily inside __init__, so
people who aren't using SES don't need it installed at all.

Required environment variables:
    AWS_ACCESS_KEY_ID       IAM user/role credentials with ses:SendEmail permission
    AWS_SECRET_ACCESS_KEY
    AWS_REGION              e.g. us-east-1 - must match the region your SES
                            sending identity is verified in

Install boto3 first if you plan to use this provider:
    pip install boto3
"""
import os

from app.services.notifications.base import EmailProvider, ProviderNotConfiguredError, NotificationError


class SESProvider(EmailProvider):
    def __init__(self):
        self.region = os.environ.get("AWS_REGION", "")
        access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

        if not self.region or not access_key or not secret_key:
            raise ProviderNotConfiguredError(
                "Amazon SES is not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, "
                "and AWS_REGION in .env"
            )

        try:
            import boto3
        except ImportError as exc:
            raise ProviderNotConfiguredError(
                "Amazon SES provider selected but boto3 isn't installed. Run: pip install boto3"
            ) from exc

        self._client = boto3.client(
            "ses",
            region_name=self.region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def send(self, *, to_email, to_name, subject, html_body, text_body=""):
        from_email = os.environ.get("EMAIL_FROM_ADDRESS", "")
        from_name = os.environ.get("EMAIL_FROM_NAME", "")
        if not from_email:
            raise ProviderNotConfiguredError("Set EMAIL_FROM_ADDRESS in .env (must be a verified SES identity)")

        body = {"Html": {"Data": html_body}}
        if text_body:
            body["Text"] = {"Data": text_body}

        try:
            self._client.send_email(
                Source=f"{from_name} <{from_email}>" if from_name else from_email,
                Destination={"ToAddresses": [to_email]},
                Message={"Subject": {"Data": subject}, "Body": body},
            )
        except Exception as exc:  # boto3 raises its own ClientError hierarchy
            raise NotificationError(f"Amazon SES send failed: {exc}") from exc
