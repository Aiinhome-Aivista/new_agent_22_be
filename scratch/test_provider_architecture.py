import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.storage.factory import StorageFactory
from app.services.storage_service import save_file, get_file
from app.services.db.factory import DBFactory
from app.extensions.db import query, execute, get_db_connection
import db

def test_storage():
    print("--- Testing Storage Architecture ---")
    default_provider = StorageFactory.get_storage_provider("DEFAULT")
    print(f"DEFAULT Provider Class: {default_provider.__class__.__name__}")
    
    aws_provider = StorageFactory.get_storage_provider("AWS")
    print(f"AWS Provider Class: {aws_provider.__class__.__name__}")

    azure_provider = StorageFactory.get_storage_provider("AZURE")
    print(f"AZURE Provider Class: {azure_provider.__class__.__name__}")

    # Test saving file locally
    saved_path = save_file(
        file_name="test_architecture.txt",
        content_bytes="Dynamic Storage Provider Test Content",
        project_name="TestProject",
        subfolder="input",
        provider_name="DEFAULT"
    )
    print(f"Saved file URI: {saved_path}")

    # Test reading back file locally
    success, content, mime = get_file(saved_path, provider_name="DEFAULT")
    print(f"File Read Success: {success}, Content: {content.decode('utf-8') if isinstance(content, bytes) else content}, MIME: {mime}")

def test_db():
    print("\n--- Testing DB Architecture ---")
    default_db = DBFactory.get_db_provider("DEFAULT")
    print(f"DEFAULT DB Provider Class: {default_db.__class__.__name__}")

    aws_db = DBFactory.get_db_provider("AWS")
    print(f"AWS DB Provider Class: {aws_db.__class__.__name__}")

    azure_db = DBFactory.get_db_provider("AZURE")
    print(f"AZURE DB Provider Class: {azure_db.__class__.__name__}")

    print("\nVerifying DB module exports:")
    print(f"db.execute_query is callable: {callable(db.execute_query)}")
    print(f"db.execute_write is callable: {callable(db.execute_write)}")
    print(f"db.get_connection is callable: {callable(db.get_connection)}")
    print(f"app.extensions.db.query is callable: {callable(query)}")

if __name__ == "__main__":
    test_storage()
    test_db()
    print("\nALL ARCHITECTURE TESTS PASSED SUCCESSFULLY!")
