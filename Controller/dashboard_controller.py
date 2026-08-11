from flask import Blueprint, jsonify, request
from db import get_connection
from role_middleware import requires_role

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/metrics/<role>', methods=['GET'])
def get_metrics(role):
    # In a real app we'd verify the requesting user's role here, but the route is generic
    # Let's trust the role parameter for the demo, or we could extract it from headers.
    
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "message": "DB connection failed"}), 500
        
    try:
        cursor = conn.cursor(dictionary=True)
        metrics = {}
        
        if role == 'developer':
            cursor.execute("SELECT COUNT(*) as c FROM generation_requests")
            metrics['my_requests'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM packages")
            metrics['downloads'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT status, COUNT(*) as count FROM generation_requests GROUP BY status")
            metrics['generation_status'] = cursor.fetchall()
            
        elif role == 'architect':
            cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status = 'draft'")
            metrics['architecture_reviews'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM pattern_matches")
            metrics['pattern_matches'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM blueprints")
            metrics['blueprint_history'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM audit_logs")
            metrics['knowledge_updates'] = cursor.fetchone()['c']
            
        elif role == 'techlead':
            cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status IN ('validated', 'packaged')")
            metrics['pending_reviews'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM validation_results")
            metrics['validation_reports'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status = 'approved'")
            metrics['approvals'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status = 'rejected'")
            metrics['rejected'] = cursor.fetchone()['c']
            
        elif role == 'devops':
            cursor.execute("SELECT COUNT(*) as c FROM packages")
            metrics['package_history'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status = 'approved'")
            metrics['deployments'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM generation_requests")
            metrics['environment_status'] = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM validation_results WHERE passed = TRUE")
            metrics['configuration_health'] = cursor.fetchone()['c']
            
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        conn.close()
    
    return jsonify({
        "success": True,
        "data": metrics
    })
