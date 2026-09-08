import logging
from typing import Any, List, Dict, Optional, Tuple, Union
from app.services.db.factory import DBFactory

logger = logging.getLogger(__name__)

def get_db_connection(provider_name: Optional[str] = None) -> Any:
    """
    Returns a connection object from the active database provider's pool.
    """
    provider = DBFactory.get_db_provider(provider_name)
    return provider.get_connection()

# Alias for legacy compatibility
get_connection = get_db_connection

def query(sql: str, params: Optional[Union[Tuple, Dict, List]] = None, provider_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Executes a SELECT query using the active DB provider.
    """
    provider = DBFactory.get_db_provider(provider_name)
    return provider.query(sql, params)

# Alias for legacy compatibility
execute_query = query

def execute(sql: str, params: Optional[Union[Tuple, Dict, List]] = None, provider_name: Optional[str] = None) -> Optional[int]:
    """
    Executes an INSERT/UPDATE/DELETE query using the active DB provider.
    """
    provider = DBFactory.get_db_provider(provider_name)
    return provider.execute(sql, params)

# Alias for legacy compatibility
execute_write = execute
