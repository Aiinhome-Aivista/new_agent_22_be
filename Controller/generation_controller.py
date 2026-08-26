from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
from agents.generation_agent import generate_code
import json
import os

generation_bp = Blueprint('generation', __name__)

@generation_bp.route('/run', methods=['POST'])
def run_generation():
    data = request.json
    req_id = data.get('request_id')
    if not req_id:
        return jsonify({"success": False, "message": "request_id required"}), 400
        
    reqs = execute_query("SELECT application_id, package_name FROM generation_requests WHERE id=%s", (req_id,))
    if not reqs:
        return jsonify({"success": False, "message": "Request not found"}), 404
        
    bps = execute_query("SELECT * FROM blueprints WHERE request_id=%s AND status='approved' ORDER BY created_at DESC LIMIT 1", (req_id,))
    if not bps:
        return jsonify({"success": False, "message": "Approved blueprint not found"}), 404
        
    specs = execute_query("SELECT * FROM generation_specs WHERE request_id=%s", (req_id,))
    
    blueprint_data = json.loads(bps[0]['file_manifest'])
    generated_files, updated_blueprint = generate_code(req_id, blueprint_data, specs[0], reqs[0]['package_name'], reqs[0]['application_id'])
    
    for f in generated_files:
        execute_write(
            "INSERT INTO generated_files (request_id, file_name, file_path, file_type, file_content) VALUES (%s, %s, %s, %s, %s)",
            (req_id, f['file_name'], f['file_path'], f['file_type'], f.get('file_content', ''))
        )
        
    execute_write("UPDATE generation_requests SET status='in_progress' WHERE id=%s", (req_id,))
    
    return jsonify({"success": True, "data": generated_files})

@generation_bp.route('/request/<int:req_id>/files', methods=['GET'])
def get_files(req_id):
    files = execute_query("SELECT * FROM generated_files WHERE request_id=%s", (req_id,))
    # Read preview directly from database column
    for f in files:
        f['preview'] = f.get('file_content') or "// No content available in database"
        # ensure needs_work is passed properly
        f['needs_work'] = f.get('needs_work')
    return jsonify({"success": True, "data": files})

@generation_bp.route('/request/<int:req_id>/analyze-needs-work', methods=['POST'])
def analyze_needs_work(req_id):
    data = request.json or {}
    force = data.get('force', False)
    
    # If not forcing, check if we already have some files unanalyzed
    files = execute_query("SELECT id, file_name, file_content, needs_work FROM generated_files WHERE request_id=%s", (req_id,))
    if not files:
        return jsonify({"success": True, "data": {}})

    files_to_analyze = [f for f in files if f.get('needs_work') is None] if not force else files
    
    if not files_to_analyze:
        # All files already analyzed, just return the map
        result_map = {f['file_name']: bool(f['needs_work']) for f in files}
        return jsonify({"success": True, "data": result_map})

    try:
        import re
        result_map = {}
        from db import execute_write
        
        for f in files:
            fname = f['file_name']
            if f in files_to_analyze:
                code = f.get('file_content', '') or ""
                # Dynamically extract all comments from the code (supports Java/JS/TS, Python/Bash/YML, HTML/XML)
                comments = re.findall(r'//.*|/\*.*?\*/|#.*|<!--.*?-->', code, re.DOTALL)
                comments_text = " ".join(comments).lower()
                
                # Check for stub-indicating keywords in the comments
                needs = any(kw in comments_text for kw in ['todo', 'implement', 'logic', 'handle', 'placeholder', 'add specific'])
                
                execute_write("UPDATE generated_files SET needs_work=%s WHERE id=%s", (needs, f['id']))
                result_map[fname] = needs
            else:
                result_map[fname] = bool(f['needs_work'])
                
        return jsonify({"success": True, "data": result_map})
        
    except Exception as e:
        print("Error during analysis:", e)
        return jsonify({"success": False, "message": "Failed to analyze files"})
