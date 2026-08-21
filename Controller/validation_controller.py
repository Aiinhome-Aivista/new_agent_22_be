from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
from agents.validation_agent import validate_package
import json
from config import PACKAGE_OUTPUT_DIR
import os

validation_bp = Blueprint('validation', __name__)

@validation_bp.route('/run', methods=['POST'])
def run_validation():
    data = request.json
    req_id = data.get('request_id')
    if not req_id:
        return jsonify({"success": False, "message": "request_id required"}), 400
        
    reqs = execute_query("SELECT application_id FROM generation_requests WHERE id=%s", (req_id,))
    bps = execute_query("SELECT * FROM blueprints WHERE request_id=%s ORDER BY created_at DESC LIMIT 1", (req_id,))
    specs = execute_query("SELECT * FROM generation_specs WHERE request_id=%s", (req_id,))
    
    if not reqs or not bps or not specs:
        return jsonify({"success": False, "message": "Required data missing"}), 404
        
    out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(req_id))
    
    gen_files = execute_query("SELECT file_name, file_content FROM generated_files WHERE request_id=%s", (req_id,))
    
    results, summary = validate_package(req_id, reqs[0]['application_id'], out_dir, gen_files, specs[0])
    
    # Delete old results if any (in case of re-run)
    execute_write("DELETE FROM validation_results WHERE request_id=%s", (req_id,))
    
    for vr in results:
        execute_write(
            "INSERT INTO validation_results (request_id, rule_name, passed, severity, message) VALUES (%s, %s, %s, %s, %s)",
            (req_id, vr['rule_name'], vr['passed'], vr['severity'], vr['message'])
        )
        
    execute_write("UPDATE generation_requests SET status='validated' WHERE id=%s", (req_id,))
    
    return jsonify({"success": True, "data": {"results": results, "summary": summary}})

@validation_bp.route('/request/<int:req_id>', methods=['GET'])
def get_validation(req_id):
    results = execute_query("SELECT * FROM validation_results WHERE request_id=%s ORDER BY id ASC", (req_id,))
    return jsonify({"success": True, "data": results})

@validation_bp.route('/fix', methods=['POST'])
def fix_validation():
    data = request.json
    req_id = data.get('request_id')
    rule_name = data.get('rule_name')
    message = data.get('message')
    
    if not req_id or not rule_name:
        return jsonify({"success": False, "message": "Missing required fields"}), 400
        
    from agents.auto_fix_agent import fix_package
    try:
        success = fix_package(req_id, rule_name, message)
        if success:
            # Re-run validation natively
            reqs = execute_query("SELECT application_id FROM generation_requests WHERE id=%s", (req_id,))
            specs = execute_query("SELECT * FROM generation_specs WHERE request_id=%s", (req_id,))
            gen_files = execute_query("SELECT file_name, file_content FROM generated_files WHERE request_id=%s", (req_id,))
            out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(req_id))
            
            results, summary = validate_package(req_id, reqs[0]['application_id'], out_dir, gen_files, specs[0])
            
            execute_write("DELETE FROM validation_results WHERE request_id=%s", (req_id,))
            for vr in results:
                execute_write(
                    "INSERT INTO validation_results (request_id, rule_name, passed, severity, message) VALUES (%s, %s, %s, %s, %s)",
                    (req_id, vr['rule_name'], vr['passed'], vr['severity'], vr['message'])
                )
            return jsonify({"success": True, "message": "Auto-fix applied and validated"})
        else:
            return jsonify({"success": False, "message": "Auto-fix failed to modify files"})
    except Exception as e:
        print(f"Error in auto-fix: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
