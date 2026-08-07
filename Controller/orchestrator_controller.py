from flask import Blueprint, request, jsonify
from db import execute_query
from agents.orchestrator_agent import start_pipeline_thread

orchestrator_bp = Blueprint('orchestrator', __name__)

@orchestrator_bp.route('/run', methods=['POST'])
def run():
    data = request.json
    req_id = data.get('request_id')
    draft_mode = data.get('draft_mode', False)
    if not req_id:
        return jsonify({"success": False, "message": "request_id required"}), 400
        
    job_id = start_pipeline_thread(req_id, draft_mode)
    return jsonify({"success": True, "data": {"job_id": job_id}})

@orchestrator_bp.route('/status/<int:job_id>', methods=['GET'])
def status(job_id):
    jobs = execute_query("SELECT * FROM pipeline_jobs WHERE id=%s", (job_id,))
    if not jobs:
        return jsonify({"success": False, "message": "Job not found"}), 404
    return jsonify({"success": True, "data": jobs[0]})
