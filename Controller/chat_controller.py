from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
from llm_service import call_llm
from rag.vector_store import VectorStore
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
        
    role = request.headers.get('X-User-Role', 'developer')
    
    role_contexts = {
        'developer': "You are the Agent 22 Advisory Agent assisting a Developer. Focus your answer on code generation, implementation details, and technical topics.",
        'architect': "You are the Agent 22 Advisory Agent assisting a Solution Architect. Focus your answer on architectural standards, design patterns, and system blueprints.",
        'techlead': "You are the Agent 22 Advisory Agent assisting a Tech Lead/Reviewer. Focus your answer on code quality, validation reports, and approval criteria.",
        'devops': "You are the Agent 22 Advisory Agent assisting a DevOps Engineer. Focus your answer on CI/CD pipelines, packaging, deployment configurations, and environments."
    }
    
    role_instruction = role_contexts.get(role, role_contexts['developer'])
        
    context = ""
    if req_id:
        specs = execute_query("SELECT * FROM generation_specs WHERE request_id=%s", (req_id,))
        bps = execute_query("SELECT class_design, generated_rationale FROM blueprints WHERE request_id=%s", (req_id,))
        if specs:
            context += f"\nRequest Specs: {json.dumps(specs[0])}"
        if bps:
            context += f"\nBlueprint context: {json.dumps(bps[0])}"
            
    try:
        vs = VectorStore()
        rag_results = vs.query(question, top_k=2)
        if rag_results and 'documents' in rag_results and rag_results['documents'] and len(rag_results['documents']) > 0:
            docs = rag_results['documents'][0]
            context += f"\n\nKnowledge Base Reference:\n" + "\n".join(docs)
    except Exception as e:
        print(f"RAG query failed: {e}")
            
    prompt = f"{role_instruction}\n\nContext:\n{context}\n\nQuestion: {question}"
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
