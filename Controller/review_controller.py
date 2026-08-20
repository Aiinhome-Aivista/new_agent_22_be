from flask import Blueprint, request, jsonify
from db import execute_query, execute_write

review_bp = Blueprint('review', __name__)

@review_bp.route('/', methods=['POST'])
def add_review():
    data = request.json
    req_id = data.get('request_id')
    decision = data.get('decision')
    if not req_id or not decision:
        return jsonify({"success": False, "message": "request_id and decision required"}), 400
        
    execute_write(
        "INSERT INTO reviews (request_id, reviewer_name, decision, comments) VALUES (%s, %s, %s, %s)",
        (req_id, data.get('reviewer_name', 'Anonymous'), decision, data.get('comments', ''))
    )
    
    if decision == 'rework':
        
        execute_write("UPDATE generation_requests SET status='rework' WHERE id=%s", (req_id,))
        execute_write("UPDATE blueprints SET status='draft' WHERE request_id=%s", (req_id,))
    else:
        execute_write("UPDATE generation_requests SET status=%s WHERE id=%s", (decision, req_id))
        
    return jsonify({"success": True, "message": "Review recorded"})


@review_bp.route('/request/<int:req_id>', methods=['GET'])
def get_reviews(req_id):
    reviews = execute_query("SELECT * FROM reviews WHERE request_id=%s ORDER BY created_at DESC", (req_id,))
    return jsonify({"success": True, "data": reviews})

@review_bp.route('/queue', methods=['GET'])
def get_review_queue():
    requests = execute_query("""
        SELECT
            gr.id,
            gr.application_id,
            gr.status,
            gr.created_at
        FROM generation_requests gr
        WHERE gr.status = 'validated'
        ORDER BY gr.created_at DESC
    """)

    return jsonify({
        "success": True,
        "data": requests
    })
