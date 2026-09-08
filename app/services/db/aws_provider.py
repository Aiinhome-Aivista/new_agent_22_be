import logging
from typing import Any, List, Dict, Optional, Tuple, Union
import mysql.connector
from mysql.connector import Error, pooling
from app.services.db.base import BaseDBProvider
from app.config.settings import (
    AWS_RDS_HOST,
    AWS_RDS_PORT,
    AWS_RDS_USER,
    AWS_RDS_PASSWORD,
    AWS_RDS_DATABASE
)

logger = logging.getLogger(__name__)

class AWSDBProvider(BaseDBProvider):
    """
    MySQL DB provider for AWS RDS.
    """

    def __init__(self):
        self.host = AWS_RDS_HOST
        self.port = AWS_RDS_PORT
        self.user = AWS_RDS_USER
        self.password = AWS_RDS_PASSWORD
        self.database = AWS_RDS_DATABASE
        self.pool = None
        self.init_pool()

    def init_pool(self) -> None:
        if not self.host or not self.database:
            logger.warning("[AWSDBProvider] AWS RDS host or database is not fully configured.")
            return
        try:
            self.pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="aws_rds_mysql_pool",
                pool_size=5,
                pool_reset_session=True,
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            logger.info(f"[AWSDBProvider] AWS RDS connection pool initialized for '{self.database}' at {self.host}:{self.port}")
        except Error as e:
            logger.warning(f"[AWSDBProvider] Could not initialize AWS RDS connection pool: {e}")
            self.pool = None

    def get_connection(self) -> Any:
        try:
            if self.pool:
                return self.pool.get_connection()
            if not self.host or not self.database:
                raise ValueError("AWS RDS configuration is incomplete.")
            return mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
        except Error as e:
            logger.error(f"[AWSDBProvider] Error getting AWS RDS connection: {e}")
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
            logger.error(f"[AWSDBProvider] Query error: {e}")
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
            logger.error(f"[AWSDBProvider] Execute error: {e}")
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
