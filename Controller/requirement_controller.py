import os
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
from agents.requirements_agent import normalize_requirements

requirement_bp = Blueprint('requirement', __name__)

@requirement_bp.route('/', methods=['POST'])
def create_requirement():
    data = dict(request.form) if request.form else (request.json or {})
    
    # Handle boolean conversion for form data
    if 'state_store_needed' in data:
        data['state_store_needed'] = data['state_store_needed'] == 'true' or data['state_store_needed'] is True

    file_upload = request.files.get('file_upload')
    sample_file_path = None
    
    if file_upload and file_upload.filename:
        filename = secure_filename(file_upload.filename)
        upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'schemas')
        os.makedirs(upload_dir, exist_ok=True)
        sample_file_path = os.path.join(upload_dir, filename)
        file_upload.save(sample_file_path)

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
            """INSERT INTO generation_specs (request_id, source_topics, target_topics, consumer_group, state_store_needed, error_topic_policy, schema_hints, sample_file_path, normalized_by) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (request_id, normalized_spec.get('source_topics'), normalized_spec.get('target_topics'), 
             normalized_spec.get('consumer_group'), normalized_spec.get('state_store_needed'), 
             normalized_spec.get('error_topic_policy'), data.get('schema_hints'), sample_file_path, 'ai')
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
    bp = execute_query("SELECT * FROM blueprints WHERE request_id=%s ORDER BY id DESC LIMIT 1", (req_id,))
    job = execute_query("SELECT * FROM pipeline_jobs WHERE request_id=%s ORDER BY id DESC LIMIT 1", (req_id,))
    val_rows = execute_query("SELECT * FROM validation_results WHERE request_id=%s", (req_id,))
    
    has_errors = any(v['severity'] == 'error' and not v['passed'] for v in val_rows) if val_rows else False
    has_warnings = any(v['severity'] == 'warning' and not v['passed'] for v in val_rows) if val_rows else False

    return jsonify({
        "success": True, 
        "data": {
            "request": req[0], 
            "spec": spec[0] if spec else None,
            "blueprint": bp[0] if bp else None,
            "job": job[0] if job else None,
            "validation_summary": {
                "results": val_rows,
                "has_errors": has_errors,
                "has_warnings": has_warnings,
                "count": len(val_rows)
            }
        }
    })

