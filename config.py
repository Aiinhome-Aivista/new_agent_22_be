import os
from dotenv import load_dotenv

load_dotenv()

# MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_mysql_password")
DB_NAME = os.getenv("DB_NAME", "agent22_kafka_db")

# LLM
LLM_API_URL = os.getenv("LLM_API_URL", "http://122.163.121.176:3041/api/generate")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral-small:24b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Internal Configs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "chroma_store")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
PACKAGE_OUTPUT_DIR = os.path.join(BASE_DIR, "generated_packages")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-agent-22-key")
FLASK_DEBUG = True

# Validation Configs
MIN_BLUEPRINT_ACCURACY = int(os.getenv("MIN_BLUEPRINT_ACCURACY", 80))
MAX_AUTO_FIX_RETRIES = int(os.getenv("MAX_AUTO_FIX_RETRIES", 5))
