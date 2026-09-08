import os
import logging
import mimetypes
from typing import Union, Optional, Tuple, Any
from werkzeug.utils import secure_filename
from app.services.storage.base import BaseStorageProvider
from app.config.settings import UPLOAD_PATH, BASE_DIR

logger = logging.getLogger(__name__)

class LocalStorageProvider(BaseStorageProvider):
    """
    Implements saving and retrieving files to local disk storage.
    """

    def __init__(self, upload_path: Optional[str] = None):
        target_path = upload_path or UPLOAD_PATH or "data/uploads"
        if os.path.isabs(target_path):
            self.upload_dir = target_path
        else:
            self.upload_dir = os.path.join(BASE_DIR, target_path)
        os.makedirs(self.upload_dir, exist_ok=True)

    def save_file(
        self,
        file_name: str,
        content_bytes: Union[bytes, bytearray, str, Any],
        project_id: Optional[Union[int, str]] = None,
        project_name: Optional[str] = None,
        subfolder: str = "input",
        **kwargs
    ) -> str:
        clean_filename = secure_filename(file_name) or "uploaded_file"
        
        # Build path structure
        path_parts = [self.upload_dir]
        if project_name or project_id:
            folder = str(project_name or project_id)
            path_parts.append(secure_filename(folder))
        if subfolder:
            path_parts.append(secure_filename(subfolder))

        target_dir = os.path.join(*path_parts)
        os.makedirs(target_dir, exist_ok=True)

        full_file_path = os.path.join(target_dir, clean_filename)

        # Convert content to bytes
        if isinstance(content_bytes, str):
            raw_data = content_bytes.encode("utf-8")
        elif isinstance(content_bytes, (bytes, bytearray)):
            raw_data = bytes(content_bytes)
        elif hasattr(content_bytes, "read"):
            if hasattr(content_bytes, "seek"):
                try:
                    content_bytes.seek(0)
                except Exception:
                    pass
            raw_data = content_bytes.read()
            if isinstance(raw_data, str):
                raw_data = raw_data.encode("utf-8")
        else:
            raise ValueError(f"Unsupported content type: {type(content_bytes)}")

        with open(full_file_path, "wb") as f:
            f.write(raw_data)

        logger.info(f"[LocalStorage] Saved file '{clean_filename}' to '{full_file_path}'")
        return full_file_path

    def get_file(self, file_uri_or_key: str) -> Tuple[bool, Union[bytes, str], Optional[str]]:
        if not os.path.exists(file_uri_or_key):
            # Check relative to upload_dir
            alt_path = os.path.join(self.upload_dir, file_uri_or_key)
            if os.path.exists(alt_path):
                file_uri_or_key = alt_path
            else:
                return False, f"File not found: {file_uri_or_key}", None

        try:
            mime_type, _ = mimetypes.guess_type(file_uri_or_key)
            with open(file_uri_or_key, "rb") as f:
                content = f.read()
            return True, content, mime_type or "application/octet-stream"
        except Exception as e:
            logger.error(f"[LocalStorage] Error reading file '{file_uri_or_key}': {e}")
            return False, str(e), None
