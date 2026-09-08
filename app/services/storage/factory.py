import logging
from typing import Optional, Dict
from app.services.storage.base import BaseStorageProvider
from app.services.storage.local_storage import LocalStorageProvider
from app.services.storage.aws_storage import AWSStorageProvider
from app.services.storage.azure_storage import AzureStorageProvider
from app.config.settings import CLOUD_PROVIDER

logger = logging.getLogger(__name__)

class StorageFactory:
    """
    Factory class to instantiate and cache storage providers based on CLOUD_PROVIDER flag.
    """
    _instances: Dict[str, BaseStorageProvider] = {}

    @classmethod
    def get_storage_provider(cls, provider_name: Optional[str] = None) -> BaseStorageProvider:
        selected = (provider_name or CLOUD_PROVIDER or "DEFAULT").upper()

        if selected in cls._instances:
            return cls._instances[selected]

        logger.info(f"[StorageFactory] Initializing storage provider: '{selected}'")

        if selected == "AWS":
            provider = AWSStorageProvider()
        elif selected == "AZURE":
            provider = AzureStorageProvider()
        elif selected in ("DEFAULT", "LOCAL"):
            provider = LocalStorageProvider()
        else:
            logger.warning(f"[StorageFactory] Unknown provider '{selected}', falling back to LocalStorageProvider.")
            provider = LocalStorageProvider()

        cls._instances[selected] = provider
        return provider
