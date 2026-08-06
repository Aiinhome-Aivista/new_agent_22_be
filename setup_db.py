import mysql.connector
from mysql.connector import Error
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
import os
import subprocess
import bcrypt

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
        hashed_pw = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        users = [
            (1, 'Rahul Ghosh', 'Developer', 'developer@example.com', hashed_pw, 'Provides topic names...'),
            (2, 'Sanjib Sau', 'Solution Architect', 'architect@example.com', hashed_pw, 'Provides messaging pattern...'),
            (3, 'Sneha Sen', 'Tech Lead', 'techlead@example.com', hashed_pw, 'Reviews validation report...'),
            (4, 'Rakesh Singh', 'Platform / DevOps Engineer', 'devops@example.com', hashed_pw, 'Reviews CI/CD, packaging...')
        ]
        # Clear users table first so we get the new names
        cursor.execute("DROP TABLE IF EXISTS users")
        # Ensure the schema is recreated since we dropped it
        cursor.close()
        conn.close()
        
        run_schema()
        
        conn = mysql.connector.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
        )
        cursor = conn.cursor()
        for u in users:
            cursor.execute("INSERT IGNORE INTO users (id, name, role, email, password, description) VALUES (%s, %s, %s, %s, %s, %s)", u)
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
