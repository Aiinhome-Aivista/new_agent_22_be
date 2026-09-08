import logging
from typing import Union, Optional, Tuple, Any
from app.services.storage.factory import StorageFactory

logger = logging.getLogger(__name__)

def save_file(
    file_name: str,
    content_bytes: Union[bytes, bytearray, str, Any],
    project_id: Optional[Union[int, str]] = None,
    project_name: Optional[str] = None,
    subfolder: str = "input",
    provider_name: Optional[str] = None,
    **kwargs
) -> str:
    """
    Facade function to save a file using the active storage provider.
    Automatically routes to AWS, Azure, or Local based on CLOUD_PROVIDER flag.
    """
    provider = StorageFactory.get_storage_provider(provider_name)
    return provider.save_file(
        file_name=file_name,
        content_bytes=content_bytes,
        project_id=project_id,
        project_name=project_name,
        subfolder=subfolder,
        **kwargs
    )

def get_file(
    file_uri_or_key: str,
    provider_name: Optional[str] = None
) -> Tuple[bool, Union[bytes, str], Optional[str]]:
    """
    Facade function to retrieve a file using the active storage provider.
    """
    provider = StorageFactory.get_storage_provider(provider_name)
    return provider.get_file(file_uri_or_key)
