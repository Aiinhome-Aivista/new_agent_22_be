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
        
    blueprint_data = json.loads(bps[0]['file_manifest'])
    out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(req_id))
    
    results, summary = validate_package(req_id, reqs[0]['application_id'], out_dir, blueprint_data.get("files", []), specs[0])
    
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
