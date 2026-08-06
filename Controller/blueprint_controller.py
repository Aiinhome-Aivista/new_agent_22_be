from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
from agents.blueprint_agent import generate_blueprint
import json

blueprint_bp = Blueprint('blueprint', __name__)

@blueprint_bp.route('/generate', methods=['POST'])
def generate():
    data = request.json
    req_id = data.get('request_id')
    if not req_id:
        return jsonify({"success": False, "message": "request_id required"}), 400
        
    spec_rows = execute_query("SELECT * FROM generation_specs WHERE request_id=%s", (req_id,))
    pattern_rows = execute_query("SELECT * FROM pattern_matches WHERE request_id=%s", (req_id,))
    
    if not spec_rows:
        return jsonify({"success": False, "message": "Spec not found"}), 404
        
    blueprint = generate_blueprint(spec_rows[0], pattern_rows)
    
    file_manifest = json.dumps({"files": blueprint.get("files", [])})
    class_design = blueprint.get("class_design", "")
    rationale = blueprint.get("rationale", "")
    
    execute_write(
        "INSERT INTO blueprints (request_id, file_manifest, class_design, generated_rationale, status) VALUES (%s, %s, %s, %s, 'draft')",
        (req_id, file_manifest, class_design, rationale)
    )
    
    return jsonify({"success": True, "data": blueprint})

@blueprint_bp.route('/<int:bp_id>/approve', methods=['PUT'])
def approve(bp_id):
    res = execute_write("UPDATE blueprints SET status='approved' WHERE id=%s", (bp_id,))
    if res is not None:
        return jsonify({"success": True, "message": "Blueprint approved"})
    return jsonify({"success": False, "message": "Update failed"}), 500

@blueprint_bp.route('/request/<int:req_id>', methods=['GET'])
def get_blueprint(req_id):
    bp = execute_query("SELECT * FROM blueprints WHERE request_id=%s ORDER BY created_at DESC LIMIT 1", (req_id,))
    if not bp:
        return jsonify({"success": False, "message": "Not found"}), 404
    bp[0]['file_manifest'] = json.loads(bp[0]['file_manifest']) if bp[0]['file_manifest'] else {"files": []}
    return jsonify({"success": True, "data": bp[0]})
