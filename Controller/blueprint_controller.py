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
    alternative_designs = json.dumps(blueprint.get("alternative_designs", []))
    assumptions = json.dumps(blueprint.get("assumptions", []))
    mermaid_diagram = blueprint.get("mermaid_diagram", "")
    
    execute_write(
        "INSERT INTO blueprints (request_id, file_manifest, class_design, generated_rationale, alternative_designs, assumptions, mermaid_diagram, status) VALUES (%s, %s, %s, %s, %s, %s, %s, 'draft')",
        (req_id, file_manifest, class_design, rationale, alternative_designs, assumptions, mermaid_diagram)
    )
    
    return jsonify({"success": True, "data": blueprint})

@blueprint_bp.route('/<int:bp_id>/approve', methods=['PUT'])
def approve(bp_id):
    res = execute_write("UPDATE blueprints SET status='approved' WHERE id=%s", (bp_id,))
    if res is not None:
        bps = execute_query("SELECT request_id FROM blueprints WHERE id=%s", (bp_id,))
        if bps:
            req_id = bps[0]['request_id']
            execute_write("UPDATE generation_requests SET status='in_progress' WHERE id=%s", (req_id,))
            from agents.orchestrator_agent import start_pipeline_thread
            start_pipeline_thread(req_id, draft_mode=False)
        return jsonify({"success": True, "message": "Blueprint approved and generation pipeline started"})
    return jsonify({"success": False, "message": "Update failed"}), 500

@blueprint_bp.route('/<int:bp_id>/rework', methods=['PUT'])
def rework(bp_id):
    data = request.json
    comments = data.get('comments', '')
    res = execute_write("UPDATE blueprints SET status='rework', comments=%s WHERE id=%s", (comments, bp_id))
    if res is not None:
        return jsonify({"success": True, "message": "Blueprint marked for rework"})
    return jsonify({"success": False, "message": "Update failed"}), 500

@blueprint_bp.route('/request/<int:req_id>', methods=['GET'])
def get_blueprint(req_id):
    bp = execute_query("SELECT * FROM blueprints WHERE request_id=%s ORDER BY created_at DESC LIMIT 1", (req_id,))
    if not bp:
        return jsonify({"success": False, "message": "Not found"}), 404
    bp[0]['file_manifest'] = json.loads(bp[0]['file_manifest']) if bp[0]['file_manifest'] else {"files": []}
    bp[0]['alternative_designs'] = json.loads(bp[0]['alternative_designs']) if bp[0]['alternative_designs'] else []
    bp[0]['assumptions'] = json.loads(bp[0]['assumptions']) if bp[0]['assumptions'] else []
    return jsonify({"success": True, "data": bp[0]})
