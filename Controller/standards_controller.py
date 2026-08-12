import os
import subprocess
from flask import Blueprint, request, jsonify

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
                    
                standards.append({
                    "id": rel_path.replace('\\', '/'),
                    "filename": file,
                    "folder": os.path.basename(root),
                    "content": content
                })
                
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
        
    trigger_ingest()
    
    return jsonify({"success": True, "message": "Standard saved successfully"})

@standards_bp.route('/<path:file_id>', methods=['DELETE'])
def delete_standard(file_id):
    file_path = os.path.join(KB_DIR, file_id)
    if os.path.exists(file_path) and file_path.endswith('.md') and KB_DIR in os.path.abspath(file_path):
        os.remove(file_path)
        trigger_ingest()
        return jsonify({"success": True, "message": "Deleted successfully"})
    
    return jsonify({"success": False, "message": "File not found"}), 404
