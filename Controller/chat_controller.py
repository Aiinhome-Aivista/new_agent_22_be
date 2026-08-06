from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
from llm_service import call_llm
import json

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/ask', methods=['POST'])
def ask():
    data = request.json
    session_id = data.get('session_id')
    question = data.get('question')
    req_id = data.get('request_id')
    
    if not session_id or not question:
        return jsonify({"success": False, "message": "session_id and question required"}), 400
        
    context = ""
    if req_id:
        specs = execute_query("SELECT * FROM generation_specs WHERE request_id=%s", (req_id,))
        bps = execute_query("SELECT class_design, generated_rationale FROM blueprints WHERE request_id=%s", (req_id,))
        if specs:
            context += f"\nSpecs: {json.dumps(specs[0])}"
        if bps:
            context += f"\nBlueprint: {json.dumps(bps[0])}"
            
    prompt = f"You are the Advisory Agent. Answer the question based on this context:\n{context}\n\nQuestion: {question}"
    answer = call_llm(prompt)
    
    execute_write(
        "INSERT INTO chat_history (session_id, question, answer, request_id) VALUES (%s, %s, %s, %s)",
        (session_id, question, answer, req_id)
    )
    
    return jsonify({"success": True, "data": {"answer": answer}})

@chat_bp.route('/history/<session_id>', methods=['GET'])
def history(session_id):
    hist = execute_query("SELECT * FROM chat_history WHERE session_id=%s ORDER BY created_at ASC", (session_id,))
    return jsonify({"success": True, "data": hist})
