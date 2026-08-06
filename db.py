import mysql.connector
from mysql.connector import Error
import logging
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger(__name__)

# Note: In a real production setup, we would initialize the pool once the DB is known to exist.
# For simplicity here, get_connection() will create a fresh connection each time or we can use a helper
# Since setup_db.py creates the database, if we try to pool with database=DB_NAME before it exists, it fails.
# We will create connections on demand for flexibility in this demo.

def get_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Error as e:
        logger.error(f"Error getting connection: {e}")
        return None

def execute_query(query, params=None):
    """Executes a read query and returns the results as a list of dictionaries."""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        return results
    except Error as e:
        logger.error(f"Error executing query: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def execute_write(query, params=None):
    """Executes a write query (INSERT/UPDATE/DELETE) and returns the last inserted row id."""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        logger.error(f"Error executing write: {e}")
        conn.rollback()
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
