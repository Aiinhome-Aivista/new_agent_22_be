import mysql.connector
from mysql.connector import Error
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
import os
import subprocess

def create_database():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        print(f"Database {DB_NAME} checked/created successfully.")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error while connecting to MySQL or creating DB: {e}")

def run_schema():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()
        schema_path = os.path.join(os.path.dirname(__file__), 'models', 'schema.sql')
        if not os.path.exists(schema_path):
            print(f"Schema file not found at {schema_path}")
            return
        
        with open(schema_path, 'r') as f:
            sql_script = f.read()
        
        # Split script into statements and execute
        statements = sql_script.split(';')
        for statement in statements:
            if statement.strip():
                cursor.execute(statement)
        conn.commit()
        print("Schema executed successfully.")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error while running schema: {e}")

def ingest_knowledge_base():
    try:
        ingest_path = os.path.join(os.path.dirname(__file__), 'rag', 'ingest.py')
        if os.path.exists(ingest_path):
            print("Running ingest.py...")
            subprocess.run(['python', ingest_path], check=True)
            print("Knowledge base ingested successfully.")
        else:
            print(f"Ingest script not found at {ingest_path}")
    except Exception as e:
        print(f"Error while running ingest.py: {e}")

if __name__ == '__main__':
    create_database()
    run_schema()
    print("Database setup complete.")
