import os
from dotenv import load_dotenv

load_dotenv()

# Global Provider Selection Flags (DEFAULT, AWS, AZURE)
CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "DEFAULT").upper()
DB_PROVIDER = os.getenv("DB_PROVIDER", "DEFAULT").upper()

# Storage Configurations
UPLOAD_PATH = os.getenv("UPLOAD_PATH", "data/uploads")

# AWS Storage Settings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME", "agent-initiative-bucket")
AWS_S3_BASE_FOLDER = os.getenv("AWS_S3_BASE_FOLDER", "Agents_Doc")
AWS_S3_AGENT_FOLDER = os.getenv("AWS_S3_AGENT_FOLDER", "Agent_22")

# Azure Storage Settings
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "agent22-container")

# Database Configurations - Local MySQL (DB_PROVIDER=DEFAULT)
MYSQL_HOST = os.getenv("MYSQL_HOST") or os.getenv("DB_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT") or os.getenv("DB_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER") or os.getenv("DB_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME", "agent22_kafka_db")

# Database Configurations - AWS RDS MySQL (DB_PROVIDER=AWS)
AWS_RDS_HOST = os.getenv("AWS_RDS_HOST", "")
AWS_RDS_PORT = int(os.getenv("AWS_RDS_PORT", 3306))
AWS_RDS_USER = os.getenv("AWS_RDS_USER", "")
AWS_RDS_PASSWORD = os.getenv("AWS_RDS_PASSWORD", "")
AWS_RDS_DATABASE = os.getenv("AWS_RDS_DATABASE", "")

# Database Configurations - Azure Database for MySQL (DB_PROVIDER=AZURE)
AZURE_DB_HOST = os.getenv("AZURE_DB_HOST", "")
AZURE_DB_PORT = int(os.getenv("AZURE_DB_PORT", 3306))
AZURE_DB_USER = os.getenv("AZURE_DB_USER", "")
AZURE_DB_PASSWORD = os.getenv("AZURE_DB_PASSWORD", "")
AZURE_DB_DATABASE = os.getenv("AZURE_DB_DATABASE", "")

# Legacy DB Fallback values
DB_HOST = MYSQL_HOST
DB_PORT = MYSQL_PORT
DB_USER = MYSQL_USER
DB_PASSWORD = MYSQL_PASSWORD
DB_NAME = MYSQL_DATABASE

# LLM & Application Settings
LLM_API_URL = os.getenv("LLM_API_URL", "http://122.163.121.176:3041/api/generate")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral-small:24b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "chroma_store")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
PACKAGE_OUTPUT_DIR = os.path.join(BASE_DIR, "generated_packages")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-agent-22-key")
FLASK_DEBUG = True

MIN_BLUEPRINT_ACCURACY = int(os.getenv("MIN_BLUEPRINT_ACCURACY", 80))
MAX_AUTO_FIX_RETRIES = int(os.getenv("MAX_AUTO_FIX_RETRIES", 5))
