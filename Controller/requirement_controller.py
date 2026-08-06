from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
from agents.requirements_agent import normalize_requirements

requirement_bp = Blueprint('requirement', __name__)

@requirement_bp.route('/', methods=['POST'])
def create_requirement():
    data = request.json
    try:
        # Validate and normalize
        normalized_spec = normalize_requirements(data)
        
        # Save request
        request_id = execute_write(
            "INSERT INTO generation_requests (request_name, application_id, package_name, requested_by) VALUES (%s, %s, %s, %s)",
            (data.get('request_name', 'Untitled'), data.get('application_id'), data.get('package_name'), data.get('requested_by', 'User'))
        )
        
        if not request_id:
            return jsonify({"success": False, "message": "Failed to save request"}), 500
            
        # Save spec
        execute_write(
            """INSERT INTO generation_specs (request_id, source_topics, target_topics, consumer_group, state_store_needed, error_topic_policy, schema_hints, normalized_by) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (request_id, normalized_spec.get('source_topics'), normalized_spec.get('target_topics'), 
             normalized_spec.get('consumer_group'), normalized_spec.get('state_store_needed'), 
             normalized_spec.get('error_topic_policy'), data.get('schema_hints'), 'ai')
        )
        
        return jsonify({"success": True, "data": {"request_id": request_id, "spec": normalized_spec}}), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@requirement_bp.route('/', methods=['GET'])
def list_requirements():
    status = request.args.get('status')
    if status:
        reqs = execute_query("SELECT * FROM generation_requests WHERE status=%s ORDER BY created_at DESC", (status,))
    else:
        reqs = execute_query("SELECT * FROM generation_requests ORDER BY created_at DESC")
    return jsonify({"success": True, "data": reqs})

@requirement_bp.route('/<int:req_id>', methods=['GET'])
def get_requirement(req_id):
    req = execute_query("SELECT * FROM generation_requests WHERE id=%s", (req_id,))
    if not req:
        return jsonify({"success": False, "message": "Not found"}), 404
    spec = execute_query("SELECT * FROM generation_specs WHERE request_id=%s", (req_id,))
    return jsonify({"success": True, "data": {"request": req[0], "spec": spec[0] if spec else None}})
