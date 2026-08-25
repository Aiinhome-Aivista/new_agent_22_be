from flask import Blueprint, jsonify, request
from db import get_connection
from role_middleware import requires_role

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/metrics/<role>', methods=['GET'])
def get_metrics(role):
    track_id = request.args.get('track_id')
    
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "message": "DB connection failed"}), 500
        
    try:
        cursor = conn.cursor(dictionary=True)
        metrics = {}
        
        if role == 'developer':
            if track_id:
                cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE track_id = %s", (track_id,))
                metrics['my_requests'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT COUNT(*) as c FROM packages WHERE request_id IN (SELECT id FROM generation_requests WHERE track_id = %s)", (track_id,))
                metrics['downloads'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT status, COUNT(*) as count FROM generation_requests WHERE track_id = %s GROUP BY status", (track_id,))
                metrics['generation_status'] = cursor.fetchall()
            else:
                cursor.execute("SELECT COUNT(*) as c FROM generation_requests")
                metrics['my_requests'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT COUNT(*) as c FROM packages")
                metrics['downloads'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT status, COUNT(*) as count FROM generation_requests GROUP BY status")
                metrics['generation_status'] = cursor.fetchall()
            
        elif role == 'architect':
            if track_id:
                cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status = 'draft' AND track_id = %s", (track_id,))
                metrics['architecture_reviews'] = cursor.fetchone()['c']
                
                try:
                    cursor.execute("SELECT COUNT(*) as c FROM pattern_matches WHERE request_id IN (SELECT id FROM generation_requests WHERE track_id = %s)", (track_id,))
                    metrics['pattern_matches'] = cursor.fetchone()['c']
                except Exception:
                    metrics['pattern_matches'] = 0
                
                cursor.execute("SELECT COUNT(*) as c FROM blueprints WHERE request_id IN (SELECT id FROM generation_requests WHERE track_id = %s)", (track_id,))
                metrics['blueprint_history'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT COUNT(*) as c FROM architecture_standards WHERE track_id = %s OR track_id IS NULL", (track_id,))
                metrics['knowledge_updates'] = cursor.fetchone()['c']
            else:
                cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status = 'draft'")
                metrics['architecture_reviews'] = cursor.fetchone()['c']
                
                try:
                    cursor.execute("SELECT COUNT(*) as c FROM pattern_matches")
                    metrics['pattern_matches'] = cursor.fetchone()['c']
                except Exception:
                    metrics['pattern_matches'] = 0
                
                cursor.execute("SELECT COUNT(*) as c FROM blueprints")
                metrics['blueprint_history'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT COUNT(*) as c FROM architecture_standards")
                metrics['knowledge_updates'] = cursor.fetchone()['c']
            
        elif role == 'techlead':
            if track_id:
                cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status = 'validated' AND track_id = %s", (track_id,))
                metrics['pending_reviews'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT COUNT(*) as c FROM validation_results WHERE request_id IN (SELECT id FROM generation_requests WHERE track_id = %s)", (track_id,))
                metrics['validation_reports'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status IN ('approved', 'packaged') AND track_id = %s", (track_id,))
                metrics['approvals'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status = 'rejected' AND track_id = %s", (track_id,))
                metrics['rejected'] = cursor.fetchone()['c']
            else:
                cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status = 'validated'")
                metrics['pending_reviews'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT COUNT(*) as c FROM validation_results")
                metrics['validation_reports'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status IN ('approved', 'packaged')")
                metrics['approvals'] = cursor.fetchone()['c']
                
                cursor.execute("SELECT COUNT(*) as c FROM generation_requests WHERE status = 'rejected'")
                metrics['rejected'] = cursor.fetchone()['c']
            
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        conn.close()
    
    return jsonify({
        "success": True,
        "data": metrics
    })
