import json
from flask import Blueprint, request, jsonify, Response
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

@techlead_bp.route('/reports/summary', methods=['GET'])
def get_reports_summary():
    # 1. total_passed: Count of requests with NO failed/warning validations
    # (Simplified: requests in packaged/approved state that have no error records)
    total_reqs = execute_query("SELECT id FROM generation_requests WHERE status IN ('validated', 'packaged', 'approved')")
    total_passed = 0
    for req in total_reqs:
        errors = execute_query("SELECT id FROM validation_results WHERE request_id=%s AND passed=0", (req['id'],))
        if not errors:
            total_passed += 1

    # 2. warnings_and_waivers: count of validation_results with severity in ('warning','info') or status='WAIVED'
    res = execute_query("SELECT COUNT(*) as count FROM validation_results WHERE severity IN ('warning','info') OR status='WAIVED'")
    warnings = res[0]['count'] if res else 0

    # 3. critical_failures: count of OPEN error severity issues
    res2 = execute_query("SELECT COUNT(*) as count FROM validation_results WHERE severity='error' AND (status='OPEN' OR status IS NULL)")
    critical = res2[0]['count'] if res2 else 0

    return jsonify({
        "success": True, 
        "data": {
            "total_passed": total_passed,
            "warnings_and_waivers": warnings,
            "critical_failures": critical
        }
    })

@techlead_bp.route('/reports', methods=['GET'])
def get_reports_list():
    # Fetch completed or packaged generation requests as reports
    query = """
        SELECT id, request_name as title, application_id, 'JSON' as type, created_at as date
        FROM generation_requests
        WHERE status IN ('validated', 'packaged', 'approved')
        ORDER BY created_at DESC
    """
    results = execute_query(query)
    
    for row in results:
        # Mocking size for UI
        row['size'] = f"{100 + (row['id'] * 15)} KB"
        # Format date for UI
        if row['date']:
            row['date'] = row['date'].strftime('%Y-%m-%d')
            
    return jsonify({"success": True, "data": results})

@techlead_bp.route('/reports/download/<int:report_id>', methods=['GET'])
def download_report(report_id):
    # Fetch full data to construct a JSON report
    req = execute_query("SELECT * FROM generation_requests WHERE id=%s", (report_id,))
    if not req:
        return jsonify({"success": False, "message": "Report not found"}), 404
        
    spec = execute_query("SELECT * FROM generation_specs WHERE request_id=%s", (report_id,))
    validations = execute_query("SELECT * FROM validation_results WHERE request_id=%s", (report_id,))
    
    report_data = {
        "report_metadata": {
            "id": report_id,
            "generated_on": str(req[0]['created_at']),
            "title": f"Audit Report for {req[0]['request_name']}"
        },
        "request_details": req[0],
        "specification": spec[0] if spec else {},
        "validations": validations or []
    }
    
    json_data = json.dumps(report_data, default=str, indent=4)
    
    return Response(
        json_data,
        mimetype="application/json",
        headers={"Content-disposition": f"attachment; filename=audit_report_{report_id}.json"}
    )
