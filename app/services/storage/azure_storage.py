import os
import logging
import mimetypes
from typing import Union, Optional, Tuple, Any
from werkzeug.utils import secure_filename
from app.services.storage.base import BaseStorageProvider
from app.config.settings import AZURE_STORAGE_CONNECTION_STRING, AZURE_CONTAINER_NAME

logger = logging.getLogger(__name__)

try:
    from azure.storage.blob import BlobServiceClient
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False
    logger.warning("azure-storage-blob is not installed. Azure Storage Provider will require azure-storage-blob.")

class AzureStorageProvider(BaseStorageProvider):
    """
    Implements saving and retrieving files using Azure Blob Storage.
    """

    def __init__(self):
        self.connection_string = AZURE_STORAGE_CONNECTION_STRING
        self.container_name = AZURE_CONTAINER_NAME or "agent22-container"

    def _get_client(self):
        if not AZURE_SDK_AVAILABLE:
            raise RuntimeError("azure-storage-blob library is not installed.")
        if not self.connection_string:
            raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING environment variable is not configured.")
        return BlobServiceClient.from_connection_string(self.connection_string)

    def _generate_blob_name(self, filename: str, project_name: Optional[str] = None, subfolder: str = "input") -> str:
        clean_name = secure_filename(filename) or "uploaded_file"
        folder_label = secure_filename(project_name) if project_name else os.path.splitext(clean_name)[0] or "unnamed"
        if subfolder:
            return f"{folder_label}/{subfolder}/{clean_name}"
        return f"{folder_label}/{clean_name}"

    def save_file(
        self,
        file_name: str,
        content_bytes: Union[bytes, bytearray, str, Any],
        project_id: Optional[Union[int, str]] = None,
        project_name: Optional[str] = None,
        subfolder: str = "input",
        **kwargs
    ) -> str:
        blob_name = kwargs.get("blob_name") or self._generate_blob_name(file_name, project_name, subfolder)
        mime_type, _ = mimetypes.guess_type(file_name)
        content_type = mime_type or "application/octet-stream"

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
            service_client = self._get_client()
            container_client = service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()

            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(payload, overwrite=True, content_type=content_type)

            azure_url = blob_client.url
            logger.info(f"[AzureStorage] Uploaded '{file_name}' to blob '{blob_name}'")
            return azure_url
        except Exception as e:
            logger.error(f"[AzureStorage] Error uploading blob: {e}")
            raise RuntimeError(f"Azure Blob upload failed: {e}")

    def get_file(self, file_uri_or_key: str) -> Tuple[bool, Union[bytes, str], Optional[str]]:
        try:
            service_client = self._get_client()
            container_client = service_client.get_container_client(self.container_name)
            blob_client = container_client.get_blob_client(file_uri_or_key)
            download_stream = blob_client.download_blob()
            content = download_stream.readall()
            properties = blob_client.get_blob_properties()
            mime_type = properties.content_settings.content_type if properties.content_settings else "application/octet-stream"
            return True, content, mime_type
        except Exception as e:
            logger.error(f"[AzureStorage] Error fetching blob '{file_uri_or_key}': {e}")
            return False, str(e), None
