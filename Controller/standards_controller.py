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

def ensure_standards_track_columns():
    try:
        cols = execute_query("SHOW COLUMNS FROM architecture_standards")
        col_names = [c['Field'] for c in cols] if cols else []
        if 'track_id' not in col_names:
            execute_write("ALTER TABLE architecture_standards ADD COLUMN track_id INT")
        if 'folder' not in col_names:
            execute_write("ALTER TABLE architecture_standards ADD COLUMN folder VARCHAR(255) DEFAULT 'standards'")
        if 'created_by' not in col_names:
            execute_write("ALTER TABLE architecture_standards ADD COLUMN created_by VARCHAR(255)")

        # Auto-normalize folder for existing standards if unassigned or default
        rows = execute_query("SELECT id, title, folder FROM architecture_standards")
        if rows:
            for r in rows:
                t = (r.get('title') or '').lower()
                cur_folder = r.get('folder') or 'standards'
                new_folder = cur_folder
                if 'pattern' in t or 'script' in t or 'sample' in t:
                    new_folder = 'sample_scripts'
                elif 'validation' in t or 'rule' in t or 'yaml' in t:
                    new_folder = 'validation_rules'
                elif 'standard' in t or 'convention' in t or 'naming' in t:
                    new_folder = 'standards'
                
                if new_folder != cur_folder:
                    execute_write("UPDATE architecture_standards SET folder = %s WHERE id = %s", (new_folder, r['id']))
        # Ensure created_by is never NULL in database
        execute_write("UPDATE architecture_standards SET created_by = 'System Architect' WHERE created_by IS NULL OR created_by = ''")
    except Exception as e:
        print(f"Error ensuring standards columns: {e}")

@standards_bp.route('/', methods=['GET'])
def list_standards():
    ensure_standards_track_columns()
    track_id = request.args.get('track_id')
    
    # 1. Fetch DB standards for this track (including fallback global standards)
    if track_id:
        db_standards = execute_query("SELECT * FROM architecture_standards WHERE track_id = %s OR track_id IS NULL ORDER BY id DESC", (track_id,))
    else:
        db_standards = execute_query("SELECT * FROM architecture_standards ORDER BY id DESC")
    
    # 2. If no DB standards exist at all, populate default standards into DB
    if not db_standards and os.path.exists(KB_DIR):
        for root, dirs, files in os.walk(KB_DIR):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    title = file.replace('.md', '').replace('_', ' ').replace('-', ' ').title()
                    folder_name = os.path.basename(root)
                    if folder_name not in ['standards', 'validation_rules', 'sample_scripts']:
                        folder_name = 'standards'
                    
                    execute_write(
                        "INSERT INTO architecture_standards (title, description, folder, created_by, track_id) VALUES (%s, %s, %s, %s, %s)",
                        (title, content, folder_name, 'System Architect', track_id)
                    )
        if track_id:
            db_standards = execute_query("SELECT * FROM architecture_standards WHERE track_id = %s OR track_id IS NULL ORDER BY id DESC", (track_id,))
        else:
            db_standards = execute_query("SELECT * FROM architecture_standards ORDER BY id DESC")

    standards = []
    if db_standards:
        for item in db_standards:
            raw_title = item.get('title', 'Standard') or 'Standard'
            filename_val = raw_title if raw_title.lower().endswith('.md') else f"{raw_title}.md"
            folder_val = item.get('folder', 'standards') or 'standards'
            if folder_val not in ['standards', 'validation_rules', 'sample_scripts']:
                folder_val = 'standards'

            standards.append({
                "id": str(item['id']),
                "db_id": item['id'],
                "filename": filename_val,
                "folder": folder_val,
                "content": item.get('description', '') or '',
                "track_id": item.get('track_id'),
                "created_by": item.get('created_by') or 'Solution Architect'
            })

    return jsonify({"success": True, "data": standards})

@standards_bp.route('/', methods=['POST'])
def save_standard():
    ensure_standards_track_columns()
    data = request.json or {}
    filename = data.get('filename', '').strip()
    folder = data.get('folder', 'standards')
    content = data.get('content', '')
    track_id = data.get('track_id')
    created_by = data.get('created_by') or 'Solution Architect'
    
    if not filename:
        return jsonify({"success": False, "message": "Filename is required"}), 400
        
    raw_name = filename[:-3] if filename.lower().endswith('.md') else filename
    clean_title = raw_name.replace('_', ' ').replace('-', ' ').title()
    clean_filename = f"{raw_name}.md"

    target_dir = os.path.join(KB_DIR, folder)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, clean_filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    try:
        if track_id:
            existing = execute_query("SELECT id FROM architecture_standards WHERE (title=%s OR title=%s) AND track_id=%s", (clean_filename, clean_title, track_id))
        else:
            existing = execute_query("SELECT id FROM architecture_standards WHERE (title=%s OR title=%s) AND track_id IS NULL", (clean_filename, clean_title))
            
        if existing:
            execute_write(
                "UPDATE architecture_standards SET title=%s, description=%s, folder=%s, created_by=%s, track_id=%s WHERE id=%s", 
                (clean_title, content, folder, created_by, track_id, existing[0]['id'])
            )
        else:
            execute_write(
                "INSERT INTO architecture_standards (title, description, folder, created_by, track_id) VALUES (%s, %s, %s, %s, %s)", 
                (clean_title, content, folder, created_by, track_id)
            )
    except Exception as db_err:
        print(f"DB save sync error: {db_err}")
        
    trigger_ingest()
    
    return jsonify({"success": True, "message": "Standard saved successfully"})

@standards_bp.route('/<path:file_id>', methods=['DELETE'])
def delete_standard(file_id):
    try:
        if file_id.isdigit():
            execute_write("DELETE FROM architecture_standards WHERE id=%s", (file_id,))
        else:
            filename = os.path.basename(file_id)
            title = filename.replace('.md', '').replace('_', ' ').replace('-', ' ').title()
            execute_write("DELETE FROM architecture_standards WHERE title=%s OR title=%s", (filename, title))
            file_path = os.path.join(KB_DIR, file_id)
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        print(f"Error deleting standard: {e}")
        
    trigger_ingest()
    return jsonify({"success": True, "message": "Standard deleted successfully"})
