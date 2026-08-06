from flask import Blueprint, request, jsonify
from db import execute_query

audit_bp = Blueprint('audit', __name__)

@audit_bp.route('/request/<int:req_id>', methods=['GET'])
def get_audit(req_id):
    logs = execute_query("SELECT * FROM audit_logs WHERE request_id=%s ORDER BY created_at ASC", (req_id,))
    return jsonify({"success": True, "data": logs})
