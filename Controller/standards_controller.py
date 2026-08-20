import os
import subprocess
from flask import Blueprint, request, jsonify
from db import execute_query, execute_write

standards_bp = Blueprint('standards', __name__)

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge_base')

def trigger_ingest():
    ingest_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rag', 'ingest.py')
    try:
        subprocess.run(['python', ingest_script], check=True)
        return True
    except Exception as e:
        print(f"Error running ingest: {e}")
        return False

@standards_bp.route('/', methods=['GET'])
def list_standards():
    standards = []
    if not os.path.exists(KB_DIR):
        return jsonify({"success": True, "data": []})
        
    for root, dirs, files in os.walk(KB_DIR):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, KB_DIR)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                title = file.replace('.md', '').replace('_', ' ').replace('-', ' ').title()

                # Sync to MySQL database architecture_standards table if missing
                db_id = 0
                try:
                    existing = execute_query("SELECT id FROM architecture_standards WHERE title=%s OR title=%s", (file, title))
                    if not existing:
                        db_id = execute_write("INSERT INTO architecture_standards (title, description) VALUES (%s, %s)", (title, content)) or 0
                    else:
                        db_id = existing[0]['id']
                except Exception as db_err:
                    print(f"DB sync notice: {db_err}")

                mtime = os.path.getmtime(file_path)
                standards.append({
                    "id": rel_path.replace('\\', '/'),
                    "db_id": db_id,
                    "filename": file,
                    "folder": os.path.basename(root),
                    "content": content,
                    "mtime": mtime
                })
                
    standards.sort(key=lambda x: (x.get('db_id', 0), x.get('mtime', 0)), reverse=True)
    return jsonify({"success": True, "data": standards})

@standards_bp.route('/', methods=['POST'])
def save_standard():
    data = request.json
    filename = data.get('filename')
    folder = data.get('folder', 'standards')
    content = data.get('content', '')
    
    if not filename:
        return jsonify({"success": False, "message": "Filename is required"}), 400
        
    if not filename.endswith('.md'):
        filename += '.md'
        
    target_dir = os.path.join(KB_DIR, folder)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    created_by = data.get('created_by') or data.get('user_id')
    title = filename.replace('.md', '').replace('_', ' ').replace('-', ' ').title()

    # Sync to DB architecture_standards table
    try:
        existing = execute_query("SELECT id FROM architecture_standards WHERE title=%s OR title=%s", (filename, title))
        if existing:
            execute_write("UPDATE architecture_standards SET title=%s, description=%s, created_by=%s WHERE id=%s", (title, content, created_by, existing[0]['id']))
        else:
            execute_write("INSERT INTO architecture_standards (title, description, created_by) VALUES (%s, %s, %s)", (title, content, created_by))
    except Exception as db_err:
        print(f"DB save sync error: {db_err}")
        
    trigger_ingest()
    
    return jsonify({"success": True, "message": "Standard saved successfully"})

@standards_bp.route('/<path:file_id>', methods=['DELETE'])
def delete_standard(file_id):
    file_path = os.path.join(KB_DIR, file_id)
    if os.path.exists(file_path) and file_path.endswith('.md') and KB_DIR in os.path.abspath(file_path):
        filename = os.path.basename(file_path)
        title = filename.replace('.md', '').replace('_', ' ').replace('-', ' ').title()
        os.remove(file_path)

        # Sync delete from DB architecture_standards table
        try:
            execute_write("DELETE FROM architecture_standards WHERE title=%s OR title=%s", (filename, title))
        except Exception as db_err:
            print(f"DB delete sync error: {db_err}")

        trigger_ingest()
        return jsonify({"success": True, "message": "Deleted successfully"})
    
    return jsonify({"success": False, "message": "File not found"}), 404
