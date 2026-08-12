from db import execute_write

execute_write("ALTER TABLE validation_results ADD COLUMN status VARCHAR(50) DEFAULT 'OPEN'")
print("Migration complete")
