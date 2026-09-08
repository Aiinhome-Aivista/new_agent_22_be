import logging
from typing import Optional, Dict
from app.services.db.base import BaseDBProvider
from app.services.db.default_provider import DefaultDBProvider
from app.services.db.aws_provider import AWSDBProvider
from app.services.db.azure_provider import AzureDBProvider
from app.config.settings import DB_PROVIDER

logger = logging.getLogger(__name__)

class DBFactory:
    """
    Factory class to instantiate and cache Database providers based on DB_PROVIDER flag.
    """
    _instances: Dict[str, BaseDBProvider] = {}

    @classmethod
    def get_db_provider(cls, provider_name: Optional[str] = None) -> BaseDBProvider:
        selected = (provider_name or DB_PROVIDER or "DEFAULT").upper()

        if selected in cls._instances:
            return cls._instances[selected]

        logger.info(f"[DBFactory] Initializing DB provider: '{selected}'")

        if selected == "AWS":
            provider = AWSDBProvider()
        elif selected == "AZURE":
            provider = AzureDBProvider()
        elif selected in ("DEFAULT", "LOCAL"):
            provider = DefaultDBProvider()
        else:
            logger.warning(f"[DBFactory] Unknown DB provider '{selected}', falling back to DefaultDBProvider.")
            provider = DefaultDBProvider()

        cls._instances[selected] = provider
        return provider
