from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Tuple, Union

class BaseDBProvider(ABC):
    """
    Abstract Base Class for Database Providers (Local MySQL, AWS RDS, Azure Database).
    """

    @abstractmethod
    def init_pool(self) -> None:
        """Initializes the database connection pool if needed."""
        pass

    @abstractmethod
    def get_connection(self) -> Any:
        """Returns a database connection instance."""
        pass

    @abstractmethod
    def query(self, sql: str, params: Optional[Union[Tuple, Dict, List]] = None) -> List[Dict[str, Any]]:
        """Executes a SELECT query and returns rows as dictionaries."""
        pass

    @abstractmethod
    def execute(self, sql: str, params: Optional[Union[Tuple, Dict, List]] = None) -> Optional[int]:
        """Executes an INSERT/UPDATE/DELETE statement and returns the last row id."""
        pass
