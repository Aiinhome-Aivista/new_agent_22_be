from flask import Blueprint, request, jsonify
from db import execute_query, execute_write

techlead_bp = Blueprint('techlead', __name__)

@techlead_bp.route('/validations', methods=['GET'])
def get_validations():
    # Join with generation_requests to get application context
    query = """
        SELECT v.*, r.application_id, r.request_name 
        FROM validation_results v
        JOIN generation_requests r ON v.request_id = r.id
        WHERE v.status = 'OPEN' OR v.status IS NULL
        ORDER BY 
            CASE v.severity 
                WHEN 'error' THEN 1 
                WHEN 'warning' THEN 2 
                WHEN 'info' THEN 3 
                ELSE 4 
            END ASC,
            v.created_at DESC
    """
    results = execute_query(query)
    
    # Map severity for frontend
    severity_map = {
        'error': 'high',
        'warning': 'medium',
        'info': 'low'
    }
    
    for row in results:
        row['severity_display'] = severity_map.get(row.get('severity', 'info'), 'low')
        
    return jsonify({"success": True, "data": results})

@techlead_bp.route('/validations/<int:val_id>/action', methods=['POST'])
def action_validation(val_id):
    data = request.json or {}
    action = data.get('action') # 'WAIVE' or 'RESOLVE'
    
    if action not in ['WAIVE', 'RESOLVE']:
        return jsonify({"success": False, "message": "Invalid action"}), 400
        
    new_status = 'WAIVED' if action == 'WAIVE' else 'RESOLVED'
    
    execute_write("UPDATE validation_results SET status=%s WHERE id=%s", (new_status, val_id))
    
    return jsonify({"success": True, "message": f"Validation {new_status}"})

@techlead_bp.route('/reviews', methods=['GET'])
def get_reviews():
    # Tech lead needs to review requests that have generated blueprints and code
    # typically status IN ('validated', 'packaged') waiting for final 'approved' (to git)
    # The architecture spec states TechLead reviews code for commit
    query = """
        SELECT r.id, r.request_name as serviceName, r.application_id as targetAppId, r.status, r.created_at as date
        FROM generation_requests r
        WHERE r.status IN ('validated', 'packaged', 'rework')
        ORDER BY r.created_at DESC
    """
    results = execute_query(query)
    
    # Let's attach validation summary
    for req in results:
        req_id = req['id']
        val_rows = execute_query("SELECT * FROM validation_results WHERE request_id=%s AND passed=0", (req_id,))
        if not val_rows:
            req['validationStatus'] = '100% Passed'
        else:
            has_errors = any(v['severity'] == 'error' for v in val_rows)
            req['validationStatus'] = 'Failed' if has_errors else 'Passed with Warnings'
            
    return jsonify({"success": True, "data": results})

@techlead_bp.route('/reviews/signoff', methods=['POST'])
def signoff_review():
    data = request.json or {}
    request_id = data.get('request_id')
    decision = data.get('decision') # 'approved' or 'rework'
    comments = data.get('comments', '')
    reviewer_name = data.get('reviewer_name', 'Tech Lead')
    
    if decision not in ['approved', 'rework', 'rejected']:
        return jsonify({"success": False, "message": "Invalid decision"}), 400
        
    # Save review record
    execute_write(
        "INSERT INTO reviews (request_id, reviewer_name, decision, comments) VALUES (%s, %s, %s, %s)",
        (request_id, reviewer_name, decision, comments)
    )
    
    # Update request status
    # If TechLead approves code, it goes to 'approved' (ready for commit) or maybe 'completed'
    # According to our schema enum, we have 'approved', 'packaged', 'rework'
    execute_write("UPDATE generation_requests SET status=%s WHERE id=%s", (decision, request_id))
    
    return jsonify({"success": True, "message": f"Sign-off recorded as {decision}"})
