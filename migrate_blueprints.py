from db import execute_write

def migrate():
    # 1. Modify the enum status
    execute_write("ALTER TABLE blueprints MODIFY COLUMN status ENUM('draft','approved','rework','rejected') DEFAULT 'draft'")
    print("Modified status ENUM")
    
    # 2. Add alternative_designs (ignore if already exists)
    try:
        execute_write("ALTER TABLE blueprints ADD COLUMN alternative_designs TEXT")
        print("Added alternative_designs")
    except Exception as e:
        print(f"alternative_designs: {e}")
        
    # 3. Add assumptions
    try:
        execute_write("ALTER TABLE blueprints ADD COLUMN assumptions TEXT")
        print("Added assumptions")
    except Exception as e:
        print(f"assumptions: {e}")
        
    # 4. Add comments
    try:
        execute_write("ALTER TABLE blueprints ADD COLUMN comments TEXT")
        print("Added comments")
    except Exception as e:
        print(f"comments: {e}")
        
if __name__ == "__main__":
    migrate()
