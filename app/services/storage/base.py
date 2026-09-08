from abc import ABC, abstractmethod
from typing import Union, Optional, Tuple, Any

class BaseStorageProvider(ABC):
    """
    Abstract Base Class for Storage Providers (Local, AWS S3, Azure Blob Storage).
    """

    @abstractmethod
    def save_file(
        self,
        file_name: str,
        content_bytes: Union[bytes, bytearray, str, Any],
        project_id: Optional[Union[int, str]] = None,
        project_name: Optional[str] = None,
        subfolder: str = "input",
        **kwargs
    ) -> str:
        """
        Saves a file to the storage provider.

        Args:
            file_name: Name of the file.
            content_bytes: Content of the file as bytes, string, or file-like object.
            project_id: Optional project identifier.
            project_name: Optional project name.
            subfolder: Subfolder within project path (e.g. input/output).

        Returns:
            str: File URI or path where the file is stored.
        """
        pass

    @abstractmethod
    def get_file(self, file_uri_or_key: str) -> Tuple[bool, Union[bytes, str], Optional[str]]:
        """
        Retrieves a file from the storage provider.

        Args:
            file_uri_or_key: File URI, key, or path.

        Returns:
            Tuple[bool, Union[bytes, str], Optional[str]]: (success, content_or_error_message, mime_type)
        """
        pass
