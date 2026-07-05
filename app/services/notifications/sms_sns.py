"""Amazon SNS provider for SMS, using boto3. Like SES, this needs AWS's SigV4
signing, so boto3 is used rather than a hand-rolled HTTP call. Imported lazily so
people not using AWS don't need boto3 installed.

Required environment variables:
    AWS_ACCESS_KEY_ID       IAM user/role credentials with sns:Publish permission
    AWS_SECRET_ACCESS_KEY
    AWS_REGION              e.g. us-east-1

Install boto3 first if you plan to use this provider:
    pip install boto3

Note: SNS SMS sending defaults to "promotional" pricing/throughput in many AWS
accounts. For transactional messages like "your repair is ready", consider setting
the message attribute below to Transactional in the AWS SNS console/settings if
delivery reliability matters more than cost.
"""
import os

from app.services.notifications.base import SMSProvider, ProviderNotConfiguredError, NotificationError


class SNSProvider(SMSProvider):
    def __init__(self):
        self.region = os.environ.get("AWS_REGION", "")
        access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

        if not self.region or not access_key or not secret_key:
            raise ProviderNotConfiguredError(
                "Amazon SNS is not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, "
                "and AWS_REGION in .env"
            )

        try:
            import boto3
        except ImportError as exc:
            raise ProviderNotConfiguredError(
                "Amazon SNS provider selected but boto3 isn't installed. Run: pip install boto3"
            ) from exc

        self._client = boto3.client(
            "sns",
            region_name=self.region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def send(self, *, to_number, body):
        try:
            self._client.publish(
                PhoneNumber=to_number,
                Message=body,
                MessageAttributes={
                    "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}
                },
            )
        except Exception as exc:  # boto3 raises its own ClientError hierarchy
            raise NotificationError(f"Amazon SNS send failed: {exc}") from exc
