import logging
from typing import Any, List, Dict, Optional, Tuple, Union
import mysql.connector
from mysql.connector import Error, pooling
from app.services.db.base import BaseDBProvider
from app.config.settings import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE
)

logger = logging.getLogger(__name__)

class DefaultDBProvider(BaseDBProvider):
    """
    MySQL DB provider for local development or default hosting environment.
    """

    def __init__(self):
        self.host = MYSQL_HOST
        self.port = MYSQL_PORT
        self.user = MYSQL_USER
        self.password = MYSQL_PASSWORD
        self.database = MYSQL_DATABASE
        self.pool = None
        self.init_pool()

    def init_pool(self) -> None:
        try:
            self.pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="default_mysql_pool",
                pool_size=5,
                pool_reset_session=True,
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            logger.info(f"[DefaultDBProvider] Connection pool initialized for database '{self.database}' at {self.host}:{self.port}")
        except Error as e:
            logger.warning(f"[DefaultDBProvider] Could not initialize connection pool: {e}. On-demand connections will be used.")
            self.pool = None

    def get_connection(self) -> Any:
        try:
            if self.pool:
                return self.pool.get_connection()
            return mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
        except Error as e:
            logger.error(f"[DefaultDBProvider] Error creating database connection: {e}")
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
            logger.error(f"[DefaultDBProvider] Query error: {e}")
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
            logger.error(f"[DefaultDBProvider] Execute error: {e}")
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
