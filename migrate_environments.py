import mysql.connector
from db import get_connection

def migrate():
    connection = get_connection()
    if not connection:
        print("Could not connect to database")
        return
        
    try:
        cursor = connection.cursor(dictionary=True)
        # Create environment_configs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS environment_configs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            env_name VARCHAR(50) NOT NULL UNIQUE,
            config_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );
        """)
        print("Successfully created environment_configs table.")
        
        # Seed default data if table is empty
        cursor.execute("SELECT COUNT(*) as count FROM environment_configs")
        result = cursor.fetchone()
        if result and result['count'] == 0:
            print("Seeding default environments...")
            default_dev = '{"kafka_brokers":"dev-broker:9092","schema_registry":"http://dev-registry:8081","docker_registry":"harbor.pwc.dev","namespace":"digiconfx-dev"}'
            default_qa = '{"kafka_brokers":"qa-broker:9092","schema_registry":"http://qa-registry:8081","docker_registry":"harbor.pwc.qa","namespace":"digiconfx-qa"}'
            default_prod = '{"kafka_brokers":"prod-broker:9092,prod-broker-2:9092","schema_registry":"http://prod-registry:8081","docker_registry":"harbor.pwc.prod","namespace":"digiconfx-prod"}'
            
            cursor.execute("INSERT INTO environment_configs (env_name, config_json) VALUES ('dev', %s), ('qa', %s), ('prod', %s)", 
                           (default_dev, default_qa, default_prod))
            print("Successfully seeded environments.")
        else:
            print("Environment data already exists.")
            
        connection.commit()
    except Exception as e:
        print(f"Migration failed: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print("Running environments migration...")
    migrate()
    print("Migration complete.")
