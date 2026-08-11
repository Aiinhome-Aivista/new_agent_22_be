import threading
import traceback
import json
import logging
from db import execute_query, execute_write
from agents.requirements_agent import normalize_requirements
from agents.pattern_retrieval_agent import retrieve_patterns
from agents.blueprint_agent import generate_blueprint
from agents.generation_agent import generate_code
from agents.validation_agent import validate_package
from config import PACKAGE_OUTPUT_DIR
import os
import zipfile

logger = logging.getLogger(__name__)

def update_job_status(job_id, status, step, log_msg):
    execute_write(
        "UPDATE pipeline_jobs SET job_status=%s, current_step=%s, step_log=CONCAT(COALESCE(step_log, ''), %s) WHERE id=%s",
        (status, step, f"[{step}] {log_msg}\n", job_id)
    )

def write_audit(request_id, agent_name, action, input_sum, output_sum, error=""):
    execute_write(
        """INSERT INTO audit_logs (request_id, agent_name, action, input_summary, output_summary, error_message)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (request_id, agent_name, action, str(input_sum), str(output_sum), error)
    )

def run_pipeline(request_id, job_id, draft_mode=False):
    try:
        update_job_status(job_id, 'running', 'Initialization', 'Started pipeline execution')
        
        # 1. Fetch Request
        reqs = execute_query("SELECT * FROM generation_requests WHERE id=%s", (request_id,))
        if not reqs:
            raise Exception(f"Request {request_id} not found")
        req = reqs[0]
        
        # 2. Requirements Agent
        update_job_status(job_id, 'running', 'Requirements', 'Normalizing requirements')
        spec_row = execute_query("SELECT * FROM generation_specs WHERE request_id=%s", (request_id,))
        if not spec_row:
            raise Exception("Generation spec missing")
        spec = spec_row[0]
        write_audit(request_id, "Requirements Interpreter", "Normalize", req['request_name'], "Spec found")
        
        # 3. Pattern Retrieval Agent
        update_job_status(job_id, 'running', 'Pattern Retrieval', 'Querying knowledge base')
        patterns = retrieve_patterns(spec)
        for p in patterns:
            execute_write(
                "INSERT INTO pattern_matches (request_id, pattern_type, source_reference, similarity_score, cited_text) VALUES (%s, %s, %s, %s, %s)",
                (request_id, p['pattern_type'], p['source_reference'], p['similarity_score'], p['cited_text'])
            )
        write_audit(request_id, "Pattern Retrieval", "Retrieve", "Spec", f"Found {len(patterns)} patterns")
        
        # 4. Blueprint Agent
        update_job_status(job_id, 'running', 'Blueprint', 'Checking or generating file manifest and class design')
        existing_bps = execute_query("SELECT * FROM blueprints WHERE request_id=%s ORDER BY id DESC LIMIT 1", (request_id,))
        if existing_bps:
            bp_row = existing_bps[0]
            manifest_obj = json.loads(bp_row['file_manifest']) if bp_row['file_manifest'] else {}
            blueprint = {
                "files": manifest_obj.get("files", []),
                "class_design": bp_row['class_design'],
                "rationale": bp_row['generated_rationale']
            }
            if bp_row['status'] == 'approved':
                draft_mode = False
        else:
            blueprint = generate_blueprint(spec, patterns)
            execute_write(
                "INSERT INTO blueprints (request_id, file_manifest, class_design, generated_rationale, status) VALUES (%s, %s, %s, %s, %s)",
                (request_id, json.dumps({"files": blueprint.get("files", [])}), blueprint.get("class_design", ""), blueprint.get("rationale", ""), "draft" if draft_mode else "approved")
            )
        write_audit(request_id, "Blueprint Agent", "Design", "Patterns & Spec", "Blueprint ready")
        
        if draft_mode:
            execute_write("UPDATE generation_requests SET status='blueprint_review' WHERE id=%s", (request_id,))
            update_job_status(job_id, 'completed', 'Blueprint', 'Pipeline paused for manual blueprint review')
            return

                    
        # 5. Generation Agent
        update_job_status(job_id, 'running', 'Generation', 'Rendering Jinja2 templates')
        generated_files, updated_blueprint = generate_code(request_id, blueprint, spec, req['package_name'], req['application_id'])
        for f in generated_files:
            execute_write(
                "INSERT INTO generated_files (request_id, file_name, file_path, file_type) VALUES (%s, %s, %s, %s)",
                (request_id, f['file_name'], f['file_path'], f['file_type'])
            )
        write_audit(request_id, "Generation Agent", "Render", "Blueprint", f"Generated {len(generated_files)} files")
        execute_write("UPDATE generation_requests SET status='in_progress' WHERE id=%s", (request_id,))
        
        # 6. Validation Agent
        update_job_status(job_id, 'running', 'Validation', 'Running validation rules')
        out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(request_id))
        execute_write("DELETE FROM validation_results WHERE request_id=%s", (request_id,))
        val_results, val_summary = validate_package(request_id, req['application_id'], out_dir, updated_blueprint.get("files", []), spec)

        
        has_errors = False
        for vr in val_results:
            execute_write(
                "INSERT INTO validation_results (request_id, rule_name, passed, severity, message) VALUES (%s, %s, %s, %s, %s)",
                (request_id, vr['rule_name'], vr['passed'], vr['severity'], vr['message'])
            )
            if vr['severity'] == 'error' and not vr['passed']:
                has_errors = True
        
        write_audit(request_id, "Validation Agent", "Validate", f"{len(generated_files)} files", val_summary)
        execute_write("UPDATE generation_requests SET status='validated' WHERE id=%s", (request_id,))
        
        # 7. Packaging Agent
        if not has_errors:
            update_job_status(job_id, 'running', 'Packaging', 'Zipping generated package')
            zip_path = os.path.join(PACKAGE_OUTPUT_DIR, f"{request_id}_package.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for root, dirs, files in os.walk(out_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, out_dir)
                        zipf.write(file_path, arcname)
                        
            execute_write(
                "INSERT INTO packages (request_id, zip_path, validation_summary) VALUES (%s, %s, %s)",
                (request_id, zip_path, val_summary)
            )
            execute_write("UPDATE generation_requests SET status='packaged' WHERE id=%s", (request_id,))
            write_audit(request_id, "Packaging Agent", "Zip", "Valid files", f"Created {zip_path}")
        else:
            update_job_status(job_id, 'running', 'Packaging', 'Skipped packaging due to validation errors')
            write_audit(request_id, "Packaging Agent", "Zip", "Invalid files", "Skipped due to errors")

        update_job_status(job_id, 'completed', 'Finished', 'Pipeline completed successfully')
        
    except Exception as e:
        logger.error(f"Pipeline error: {traceback.format_exc()}")
        update_job_status(job_id, 'failed', 'Error', f"Exception: {str(e)}")
        write_audit(request_id, "Orchestrator", "Execute", "Pipeline", "Failed", str(e))

def start_pipeline_thread(request_id, draft_mode=False):
    job_id = execute_write("INSERT INTO pipeline_jobs (request_id) VALUES (%s)", (request_id,))
    t = threading.Thread(target=run_pipeline, args=(request_id, job_id, draft_mode))
    t.start()
    return job_id
