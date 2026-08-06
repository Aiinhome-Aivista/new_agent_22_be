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

def seed_users():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
        )
        cursor = conn.cursor()
        users = [
            ('developer', 'Engagement Manager', 'Engagement Manager', 'manager@example.com', 'password123', 'Provides topic names...', 'EM', 'border-emerald-600 text-emerald-600 bg-emerald-50'),
            ('architect', 'Project Lead', 'Project Lead', 'lead@example.com', 'password123', 'Provides messaging pattern...', 'PL', 'border-blue-600 text-blue-600 bg-blue-50'),
            ('techlead', 'PMO', 'PMO', 'reviewer@example.com', 'password123', 'Reviews validation report...', 'QR', 'border-purple-600 text-purple-600 bg-purple-50'),
            ('devops', 'Finance', 'Finance', 'finance@example.com', 'password123', 'Reviews CI/CD, packaging...', 'FC', 'border-amber-600 text-amber-600 bg-amber-50')
        ]
        # Clear users table first so we get the new names
        cursor.execute("TRUNCATE TABLE users")
        for u in users:
            cursor.execute("INSERT IGNORE INTO users (id, name, role, email, password, description, icon, color) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", u)
        conn.commit()
        print("Users seeded successfully.")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error seeding users: {e}")

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
    seed_users()
    print("Database setup complete.")
