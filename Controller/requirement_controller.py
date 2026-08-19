import os
import re
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
from agents.requirements_agent import normalize_requirements, analyze_conversational_intake
import json

requirement_bp = Blueprint('requirement', __name__)

def derive_app_and_package_id(request_name, app_id=None, pkg_name=None):
    clean_slug = re.sub(r'[^a-zA-Z0-9]', '', request_name or '').lower() or 'app'
    default_id = f"com.company.{clean_slug}"
    
    final_app_id = app_id.strip() if (app_id and isinstance(app_id, str) and app_id.strip()) else default_id
    final_pkg_name = pkg_name.strip() if (pkg_name and isinstance(pkg_name, str) and pkg_name.strip()) else final_app_id
    
    return final_app_id, final_pkg_name

@requirement_bp.route('/', methods=['POST'])
def create_requirement():
    data = dict(request.form) if request.form else (request.json or {})
    
    # In the NLP flow, prompt is passed
    prompt = data.get('prompt', '')
    language = data.get('language', 'Java Kafka')

    file_uploads = request.files.getlist('file_upload')
    saved_file_paths = []
    
    upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'schemas')
    os.makedirs(upload_dir, exist_ok=True)
    
    for file_upload in file_uploads:
        if file_upload and file_upload.filename:
            filename = secure_filename(file_upload.filename)
            file_path = os.path.join(upload_dir, filename)
            file_upload.save(file_path)
            saved_file_paths.append(file_path)

    try:
        # Use LLM to extract ALL requirements from the unstructured prompt
        # We pass both the prompt and the file names to the LLM agent for context
        extract_payload = {
            'prompt': prompt,
            'language': language,
            'attached_files': [os.path.basename(p) for p in saved_file_paths]
        }
        normalized_spec = normalize_requirements(extract_payload)
        
        req_name = normalized_spec.get('request_name') or 'NLP Chat Request'
        final_app_id, final_pkg_name = derive_app_and_package_id(
            req_name, 
            normalized_spec.get('application_id'), 
            normalized_spec.get('package_name')
        )
        normalized_spec['application_id'] = final_app_id
        normalized_spec['package_name'] = final_pkg_name

        # Save request
        request_id = execute_write(
            "INSERT INTO generation_requests (request_name, application_id, package_name, requested_by) VALUES (%s, %s, %s, %s)",
            (req_name, 
             final_app_id, 
             final_pkg_name, 
             data.get('requested_by', 'User'))
        )
        
        if not request_id:
            return jsonify({"success": False, "message": "Failed to save request"}), 500
            
        # Save spec
        # For multiple files, we'll store them as a JSON string in sample_file_path or just the first one if schema doesn't support array.
        # Assuming sample_file_path is a text/varchar column, we can store JSON array of paths.
        paths_str = json.dumps(saved_file_paths) if saved_file_paths else None
        
        execute_write(
            """INSERT INTO generation_specs (request_id, source_topics, target_topics, consumer_group, state_store_needed, error_topic_policy, schema_hints, sample_file_path, normalized_by) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (request_id, normalized_spec.get('source_topics'), normalized_spec.get('target_topics'), 
             normalized_spec.get('consumer_group'), normalized_spec.get('state_store_needed', False), 
             normalized_spec.get('error_topic_policy', 'DLQ'), prompt, paths_str, 'ai')
        )
        
        return jsonify({"success": True, "data": {"request_id": request_id, "spec": normalized_spec}}), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@requirement_bp.route('/intake-chat', methods=['POST'])
def intake_chat():
    messages_str = request.form.get('messages', '[]')
    try:
        messages = json.loads(messages_str)
    except Exception:
        messages = []
        
    language = request.form.get('language', 'Java Kafka')
    
    if not messages:
        return jsonify({"success": False, "message": "No messages provided"}), 400
        
    file_uploads = request.files.getlist('file_upload')
    saved_file_paths = []
    
    upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'schemas')
    os.makedirs(upload_dir, exist_ok=True)
    
    for file_upload in file_uploads:
        if file_upload and file_upload.filename:
            filename = secure_filename(file_upload.filename)
            file_path = os.path.join(upload_dir, filename)
            file_upload.save(file_path)
            saved_file_paths.append(file_path)
            
    try:
        files = [os.path.basename(p) for p in saved_file_paths]
        result = analyze_conversational_intake(messages, language, files)
        
        if result.get('status') == 'complete':
            req = result.get('requirements', {})
            req_name = req.get('request_name') or 'NLP Chat Request'
            final_app_id, final_pkg_name = derive_app_and_package_id(
                req_name, 
                req.get('application_id'), 
                req.get('package_name')
            )
            req['application_id'] = final_app_id
            req['package_name'] = final_pkg_name

            # Save request
            request_id = execute_write(
                "INSERT INTO generation_requests (request_name, application_id, package_name, requested_by) VALUES (%s, %s, %s, %s)",
                (req_name, 
                 final_app_id, 
                 final_pkg_name, 
                 'User')
            )
            
            # Save spec
            paths_str = json.dumps(saved_file_paths) if saved_file_paths else None
            execute_write(
                """INSERT INTO generation_specs (request_id, source_topics, target_topics, consumer_group, state_store_needed, error_topic_policy, schema_hints, sample_file_path, normalized_by) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (request_id, req.get('source_topics'), req.get('target_topics'), 
                 req.get('consumer_group'), req.get('state_store_needed', False), 
                 req.get('error_topic_policy', 'DLQ'), json.dumps(messages), paths_str, 'ai')
            )
            
            return jsonify({"success": True, "status": "complete", "data": {"request_id": request_id}})
        else:
            return jsonify({"success": True, "status": "more_info", "question": result.get('question', "Can you provide more details?")})
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@requirement_bp.route('/', methods=['GET'])
def list_requirements():
    status = request.args.get('status')
    query = """
        SELECT r.*, s.schema_hints 
        FROM generation_requests r 
        LEFT JOIN generation_specs s ON r.id = s.request_id
    """
    if status:
        query += " WHERE r.status=%s ORDER BY r.created_at DESC"
        reqs = execute_query(query, (status,))
    else:
        query += " ORDER BY r.created_at DESC"
        reqs = execute_query(query)
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

