from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
from agents.pattern_retrieval_agent import retrieve_patterns

pattern_bp = Blueprint('pattern', __name__)

@pattern_bp.route('/retrieve', methods=['POST'])
def retrieve():
    data = request.json
    req_id = data.get('request_id')
    if not req_id:
        return jsonify({"success": False, "message": "request_id required"}), 400
        
    spec_rows = execute_query("SELECT * FROM generation_specs WHERE request_id=%s", (req_id,))
    if not spec_rows:
        return jsonify({"success": False, "message": "Spec not found"}), 404
        
    req_rows = execute_query("SELECT track_id FROM generation_requests WHERE id=%s", (req_id,))
    track_id = req_rows[0]['track_id'] if req_rows else None
        
    patterns = retrieve_patterns(spec_rows[0], track_id=track_id)
    
    # Store in DB if table exists
    try:
        for p in patterns:
            execute_write(
                "INSERT INTO pattern_matches (request_id, pattern_type, source_reference, similarity_score, cited_text) VALUES (%s, %s, %s, %s, %s)",
                (req_id, p['pattern_type'], p['source_reference'], p['similarity_score'], p['cited_text'])
            )
    except Exception:
        pass
        
    return jsonify({"success": True, "data": patterns})

@pattern_bp.route('/request/<int:req_id>', methods=['GET'])
def get_patterns(req_id):
    try:
        patterns = execute_query("SELECT * FROM pattern_matches WHERE request_id=%s ORDER BY similarity_score DESC", (req_id,))
        return jsonify({"success": True, "data": patterns})
    except Exception:
        return jsonify({"success": True, "data": []})
