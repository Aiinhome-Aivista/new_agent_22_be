from flask import Blueprint, request, jsonify, send_file
from db import execute_query, execute_write
from config import PACKAGE_OUTPUT_DIR
from agents.packaging_agent import generate_packaging_scripts
import os
import zipfile
import json

packaging_bp = Blueprint('packaging', __name__)

@packaging_bp.route('/build', methods=['POST'])
def build_package():
    data = request.json
    req_id = data.get('request_id')
    if not req_id:
        return jsonify({"success": False, "message": "request_id required"}), 400
        
    # Check for open errors
    errors = execute_query("SELECT id FROM validation_results WHERE request_id=%s AND severity='error' AND passed=0", (req_id,))
    if errors:
        return jsonify({"success": False, "message": "Cannot build package with open validation errors"}), 400
        
    # Just mark as packaged in DB without physical zip
    zip_path = "virtual/db_stored.zip"
                
    execute_write(
        "INSERT INTO packages (request_id, zip_path, validation_summary) VALUES (%s, %s, %s)",
        (req_id, zip_path, "Built manually via API - In Memory Zip")
    )
    execute_write("UPDATE generation_requests SET status='packaged' WHERE id=%s", (req_id,))
    
    return jsonify({"success": True, "message": "Package built"})

@packaging_bp.route('/', methods=['GET'])
def list_packages():
    pkgs = execute_query("SELECT p.*, r.request_name FROM packages p JOIN generation_requests r ON p.request_id = r.id")
    return jsonify({"success": True, "data": pkgs})

@packaging_bp.route('/download/<int:pkg_id>', methods=['GET'])
def download(pkg_id):
    import io
    pkg = execute_query("SELECT request_id FROM packages WHERE id=%s", (pkg_id,))
    if not pkg:
        return jsonify({"success": False, "message": "Not found"}), 404
        
    req_id = pkg[0]['request_id']
    files = execute_query("SELECT file_name, file_path, file_content FROM generated_files WHERE request_id=%s", (req_id,))
    
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zipf:
        for f in files:
            arcname = f['file_name']
            if f.get('file_path'):
                # Try to extract the relative path from the absolute virtual path
                if 'generated_packages' in f['file_path']:
                    parts = f['file_path'].split('generated_packages')
                    if len(parts) > 1:
                        # e.g., /123/src/main/... -> src/main/...
                        sub_path = parts[1].replace('\\', '/').strip('/')
                        if '/' in sub_path:
                            arcname = sub_path.split('/', 1)[1]
            zipf.writestr(arcname, f.get('file_content', '') or '')
            
    memory_file.seek(0)
    return send_file(memory_file, download_name=f"package_{req_id}.zip", as_attachment=True)

@packaging_bp.route('/generate-scripts', methods=['POST'])
def generate_scripts():
    data = request.json
    req_id = data.get('request_id')
    env_name = data.get('env_name', 'dev')
    
    if not req_id:
        return jsonify({"success": False, "message": "request_id required"}), 400
        
    # Get Spec
    spec_rows = execute_query("SELECT * FROM generation_specs WHERE request_id = %s", (req_id,))
    if not spec_rows:
        return jsonify({"success": False, "message": "Spec not found"}), 404
    spec = spec_rows[0]
    
    # Get Env Config
    env_rows = execute_query("SELECT config_json FROM environment_configs WHERE env_name = %s", (env_name,))
    if not env_rows:
        return jsonify({"success": False, "message": "Environment config not found"}), 404
    
    try:
        env_config = json.loads(env_rows[0]['config_json'])
    except:
        env_config = {}
        
    # Get Java Files
    java_files = execute_query("SELECT file_name FROM generated_files WHERE request_id = %s", (req_id,))
    
    # Call AI Agent
    scripts = generate_packaging_scripts(spec, env_config, java_files)
    
    # Save files to disk and DB
    # Save files to DB only
    out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(req_id)).replace('\\', '/')
    
    for filename, content in [('pom.xml', scripts.get('pom_xml', '')), 
                              ('Dockerfile', scripts.get('dockerfile', '')), 
                              ('deployment.yaml', scripts.get('deployment_yaml', ''))]:
        
        file_path = f"{out_dir}/{filename}"
            
        # Update or insert into generated_files
        existing = execute_query("SELECT id FROM generated_files WHERE request_id = %s AND file_name = %s", (req_id, filename))
        if not existing:
            execute_write(
                "INSERT INTO generated_files (request_id, file_name, file_path, file_type, file_content) VALUES (%s, %s, %s, %s, %s)",
                (req_id, filename, file_path, 'yaml' if filename.endswith('.yaml') else 'xml', content)
            )
        else:
            execute_write(
                "UPDATE generated_files SET file_content=%s WHERE id=%s",
                (content, existing[0]['id'])
            )
            
    return jsonify({"success": True, "message": "Scripts generated successfully", "data": scripts})

@packaging_bp.route('/trigger-pipeline', methods=['POST'])
def trigger_pipeline():
    data = request.json
    req_id = data.get('request_id')
    env_name = data.get('env_name', 'dev')
    
    if not req_id:
        return jsonify({"success": False, "message": "request_id required"}), 400
        
    execute_write("UPDATE generation_requests SET status='packaged' WHERE id=%s", (req_id,))
    
    # Simulate a pipeline run log
    return jsonify({
        "success": True, 
        "message": f"Pipeline triggered for {env_name.upper()}",
        "log": f"Started deployment to {env_name.upper()} namespace...\\nBuilding docker image...\\nPushing to registry...\\nApplying deployment.yaml...\\nSuccess!"
    })
