import os
import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class R2Publisher:
    def __init__(self):
        self.endpoint = os.getenv("R2_ENDPOINT", "")
        self.access_key = os.getenv("R2_ACCESS_KEY", "")
        self.secret_key = os.getenv("R2_SECRET_KEY", "")
        self.bucket = os.getenv("R2_BUCKET", "leads-sites")
        self.root_domain = os.getenv("ROOT_DOMAIN", "seu-dominio.com")

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.access_key and self.secret_key)

    def publish(self, html: str, slug: str) -> Optional[str]:
        if not self.is_configured:
            logger.error("R2 not configured — skipping publish")
            return None

        key = f"{slug}/index.html"
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=html.encode("utf-8"),
                ContentType="text/html; charset=utf-8",
            )
            url = f"https://{slug}.{self.root_domain}"
            logger.info("Published %s to %s", key, url)
            return url
        except ClientError as e:
            logger.error("Failed to publish %s: %s", key, e)
            return None
