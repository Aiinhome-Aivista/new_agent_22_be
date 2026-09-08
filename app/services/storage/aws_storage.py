import os
import io
import logging
import mimetypes
from typing import Union, Optional, Tuple, Any
from werkzeug.utils import secure_filename
from app.services.storage.base import BaseStorageProvider
from app.config.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_DEFAULT_REGION,
    AWS_S3_BUCKET_NAME,
    AWS_S3_BASE_FOLDER,
    AWS_S3_AGENT_FOLDER
)

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 is not installed. AWS S3 Storage Provider will require boto3.")

class AWSStorageProvider(BaseStorageProvider):
    """
    Implements saving and retrieving files using AWS S3.
    """

    def __init__(self):
        self.bucket_name = AWS_S3_BUCKET_NAME or "agent-initiative-bucket"
        self.region = AWS_DEFAULT_REGION or "us-east-1"
        self.base_folder = AWS_S3_BASE_FOLDER or "Agents_Doc"
        self.agent_folder = AWS_S3_AGENT_FOLDER or "Agent_22"

    def _get_client(self):
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 library is not installed.")
        client_kwargs = {"region_name": self.region}
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            client_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
        return boto3.client("s3", **client_kwargs)

    def _generate_key(self, filename: str, project_name: Optional[str] = None, subfolder: str = "input") -> str:
        clean_name = secure_filename(filename) or "uploaded_file"
        folder_label = secure_filename(project_name) if project_name else os.path.splitext(clean_name)[0] or "unnamed"
        if subfolder:
            return f"{self.base_folder}/{self.agent_folder}/{folder_label}/{subfolder}/{clean_name}"
        return f"{self.base_folder}/{self.agent_folder}/{folder_label}/{clean_name}"

    def save_file(
        self,
        file_name: str,
        content_bytes: Union[bytes, bytearray, str, Any],
        project_id: Optional[Union[int, str]] = None,
        project_name: Optional[str] = None,
        subfolder: str = "input",
        **kwargs
    ) -> str:
        s3_key = kwargs.get("s3_key") or self._generate_key(file_name, project_name, subfolder)
        mime_type, _ = mimetypes.guess_type(file_name)
        content_type = mime_type or "application/octet-stream"

        # Prepare payload
        if isinstance(content_bytes, str):
            payload = content_bytes.encode("utf-8")
        elif isinstance(content_bytes, (bytes, bytearray)):
            payload = bytes(content_bytes)
        elif hasattr(content_bytes, "read"):
            if hasattr(content_bytes, "seek"):
                try:
                    content_bytes.seek(0)
                except Exception:
                    pass
            read_data = content_bytes.read()
            payload = read_data.encode("utf-8") if isinstance(read_data, str) else read_data
        else:
            raise ValueError(f"Unsupported content_bytes type: {type(content_bytes)}")

        try:
            client = self._get_client()
            client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=payload,
                ContentType=content_type
            )
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            logger.info(f"[AWSStorage] Uploaded '{file_name}' to S3 key '{s3_key}'")
            return s3_url
        except Exception as e:
            logger.error(f"[AWSStorage] Error uploading to S3: {e}")
            raise RuntimeError(f"AWS S3 upload failed: {e}")

    def get_file(self, file_uri_or_key: str) -> Tuple[bool, Union[bytes, str], Optional[str]]:
        try:
            client = self._get_client()
            s3_key = file_uri_or_key.rsplit(f"{self.bucket_name}/", 1)[-1] if self.bucket_name in file_uri_or_key else file_uri_or_key
            response = client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response["Body"].read()
            content_type = response.get("ContentType", "application/octet-stream")
            return True, content, content_type
        except Exception as e:
            logger.error(f"[AWSStorage] Error fetching '{file_uri_or_key}' from S3: {e}")
            return False, str(e), None
