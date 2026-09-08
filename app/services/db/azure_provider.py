import logging
from typing import Any, List, Dict, Optional, Tuple, Union
import mysql.connector
from mysql.connector import Error, pooling
from app.services.db.base import BaseDBProvider
from app.config.settings import (
    AZURE_DB_HOST,
    AZURE_DB_PORT,
    AZURE_DB_USER,
    AZURE_DB_PASSWORD,
    AZURE_DB_DATABASE
)

logger = logging.getLogger(__name__)

class AzureDBProvider(BaseDBProvider):
    """
    MySQL DB provider for Azure Database for MySQL.
    """

    def __init__(self):
        self.host = AZURE_DB_HOST
        self.port = AZURE_DB_PORT
        self.user = AZURE_DB_USER
        self.password = AZURE_DB_PASSWORD
        self.database = AZURE_DB_DATABASE
        self.pool = None
        self.init_pool()

    def init_pool(self) -> None:
        if not self.host or not self.database:
            logger.warning("[AzureDBProvider] Azure DB host or database is not fully configured.")
            return
        try:
            self.pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="azure_mysql_pool",
                pool_size=5,
                pool_reset_session=True,
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            logger.info(f"[AzureDBProvider] Azure DB connection pool initialized for '{self.database}' at {self.host}:{self.port}")
        except Error as e:
            logger.warning(f"[AzureDBProvider] Could not initialize Azure DB connection pool: {e}")
            self.pool = None

    def get_connection(self) -> Any:
        try:
            if self.pool:
                return self.pool.get_connection()
            if not self.host or not self.database:
                raise ValueError("Azure Database configuration is incomplete.")
            return mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
        except Error as e:
            logger.error(f"[AzureDBProvider] Error getting Azure DB connection: {e}")
            return None

    def query(self, sql: str, params: Optional[Union[Tuple, Dict, List]] = None) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        if not conn:
            return []
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params or ())
            results = cursor.fetchall()
            return results
        except Error as e:
            logger.error(f"[AzureDBProvider] Query error: {e}")
            return []
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def execute(self, sql: str, params: Optional[Union[Tuple, Dict, List]] = None) -> Optional[int]:
        conn = self.get_connection()
        if not conn:
            return None
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            conn.commit()
            return cursor.lastrowid
        except Error as e:
            logger.error(f"[AzureDBProvider] Execute error: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
