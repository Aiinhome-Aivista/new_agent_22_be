from flask import Blueprint, request, jsonify, send_file
from db import execute_query, execute_write
from config import PACKAGE_OUTPUT_DIR
import os
import zipfile

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
        
    out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(req_id))
    zip_path = os.path.join(PACKAGE_OUTPUT_DIR, f"{req_id}_package.zip")
    
    if not os.path.exists(out_dir):
        return jsonify({"success": False, "message": "Generated files not found"}), 404
        
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(out_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, out_dir)
                zipf.write(file_path, arcname)
                
    execute_write(
        "INSERT INTO packages (request_id, zip_path, validation_summary) VALUES (%s, %s, %s)",
        (req_id, zip_path, "Built manually via API")
    )
    execute_write("UPDATE generation_requests SET status='packaged' WHERE id=%s", (req_id,))
    
    return jsonify({"success": True, "message": "Package built"})

@packaging_bp.route('/', methods=['GET'])
def list_packages():
    pkgs = execute_query("SELECT p.*, r.request_name FROM packages p JOIN generation_requests r ON p.request_id = r.id")
    return jsonify({"success": True, "data": pkgs})

@packaging_bp.route('/download/<int:pkg_id>', methods=['GET'])
def download(pkg_id):
    pkg = execute_query("SELECT zip_path FROM packages WHERE id=%s", (pkg_id,))
    if not pkg or not os.path.exists(pkg[0]['zip_path']):
        return jsonify({"success": False, "message": "Not found"}), 404
    return send_file(pkg[0]['zip_path'], as_attachment=True)
