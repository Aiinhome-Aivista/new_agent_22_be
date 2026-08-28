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
from rag.vector_store import VectorStore

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

def ensure_pattern_matches_table():
    try:
        execute_write("""
            CREATE TABLE IF NOT EXISTS pattern_matches (
                id INT AUTO_INCREMENT PRIMARY KEY,
                request_id INT NOT NULL,
                pattern_type VARCHAR(255),
                source_reference VARCHAR(255),
                similarity_score FLOAT,
                cited_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX (request_id)
            )
        """)
    except Exception as e:
        pass

def run_pipeline(request_id, job_id, draft_mode=False):
    try:
        ensure_pattern_matches_table()
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
        patterns = retrieve_patterns(spec, req.get('track_id'))
        for p in patterns:
            try:
                execute_write(
                    "INSERT INTO pattern_matches (request_id, pattern_type, source_reference, similarity_score, cited_text) VALUES (%s, %s, %s, %s, %s)",
                    (request_id, p['pattern_type'], p['source_reference'], p['similarity_score'], p['cited_text'])
                )
            except Exception as err:
                print(f"Pattern match write error: {err}")
        write_audit(request_id, "Pattern Retrieval", "Retrieve", "Spec", f"Found {len(patterns)} patterns")
        
        # 4. Blueprint Agent
        update_job_status(job_id, 'running', 'Blueprint', 'Checking or generating file manifest and class design')
        existing_bps = execute_query("SELECT * FROM blueprints WHERE request_id=%s ORDER BY id DESC LIMIT 1", (request_id,))
        if existing_bps and existing_bps[0]['status'] != 'rework':
            bp_row = existing_bps[0]
            manifest_obj = json.loads(bp_row['file_manifest']) if bp_row['file_manifest'] else {}
            blueprint = {
                "files": manifest_obj.get("files", []),
                "class_design": bp_row['class_design'],
                "rationale": bp_row['generated_rationale'],
                "mermaid_diagram": bp_row.get('mermaid_diagram', '')
            }
            if bp_row['status'] == 'approved':
                draft_mode = False
        else:
            existing_files_query = execute_query("SELECT DISTINCT file_name FROM generated_files")
            existing_files = [f['file_name'] for f in existing_files_query]
            
            rework_comments = ""
            if existing_bps:
                rework_comments = existing_bps[0].get('comments') or ""
                
            blueprint = generate_blueprint(spec, patterns, existing_files, rework_comments)
            execute_write(
                "INSERT INTO blueprints (request_id, file_manifest, class_design, generated_rationale, mermaid_diagram, status) VALUES (%s, %s, %s, %s, %s, %s)",
                (request_id, json.dumps({"files": blueprint.get("files", [])}), blueprint.get("class_design", ""), blueprint.get("rationale", ""), blueprint.get("mermaid_diagram", ""), "draft" if draft_mode else "approved")
            )
        write_audit(request_id, "Blueprint Agent", "Design", "Patterns & Spec", "Blueprint ready")
        if draft_mode:
            execute_write("UPDATE generation_requests SET status='draft' WHERE id=%s", (request_id,))
            update_job_status(job_id, 'completed', 'Blueprint', 'Pipeline paused for manual blueprint review')
            return
            
        try:
            vs = VectorStore()
            bp_doc = f"Blueprint Design:\n{blueprint.get('class_design', '')}\nRationale:\n{blueprint.get('rationale', '')}"
            vs.add_documents([bp_doc], [{"request_id": request_id, "type": "blueprint", "track_id": req.get('track_id') or -1}], [f"req_{request_id}_bp"])
        except Exception as e:
            logger.error(f"Failed to add blueprint to VectorStore: {e}")

                    
        # 5. Generation Agent
        update_job_status(job_id, 'running', 'Generation', 'Rendering Jinja2 templates')
        generated_files, updated_blueprint = generate_code(request_id, blueprint, spec, req['package_name'], req['application_id'], patterns)
        
        # Copy reused files from database
        reused_files = [f for f in updated_blueprint.get("files", []) if f.get("status") == "reuse"]
        for rf in reused_files:
            past_file = execute_query("SELECT file_content, file_type, file_path FROM generated_files WHERE file_name=%s ORDER BY id DESC LIMIT 1", (rf['filename'],))
            if past_file:
                generated_files.append({
                    "file_name": rf['filename'],
                    "file_path": past_file[0]['file_path'],
                    "file_type": past_file[0]['file_type'],
                    "file_content": past_file[0]['file_content']
                })
        
        
        docs = []
        metas = []
        ids = []
        
        for idx, f in enumerate(generated_files):
            execute_write(
                "INSERT INTO generated_files (request_id, file_name, file_path, file_type, file_content) VALUES (%s, %s, %s, %s, %s)",
                (request_id, f['file_name'], f['file_path'], f['file_type'], f.get('file_content', ''))
            )
            content = f.get('file_content', '')
            if content.strip():
                docs.append(f"Generated File {f['file_name']}:\n{content}")
                metas.append({"request_id": request_id, "type": "code", "track_id": req.get('track_id') or -1})
                ids.append(f"req_{request_id}_code_{idx}")
                
        try:
            if docs:
                vs = VectorStore()
                vs.add_documents(docs, metas, ids)
        except Exception as e:
            logger.error(f"Failed to add generated code to VectorStore: {e}")
            
        write_audit(request_id, "Generation Agent", "Render", "Blueprint", f"Generated {len(generated_files)} files")
        execute_write("UPDATE generation_requests SET status='in_progress' WHERE id=%s", (request_id,))
        
        # 6. Validation Agent
        update_job_status(job_id, 'running', 'Validation', 'Running validation rules')
        out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(request_id))
        execute_write("DELETE FROM validation_results WHERE request_id=%s", (request_id,))
        val_results, val_summary = validate_package(request_id, req['application_id'], out_dir, updated_blueprint.get("files", []), spec, req.get('track_id'))

        
        has_errors = False
        for vr in val_results:
            status_val = 'RESOLVED' if vr['passed'] else 'OPEN'
            execute_write(
                "INSERT INTO validation_results (request_id, rule_name, passed, severity, message, status) VALUES (%s, %s, %s, %s, %s, %s)",
                (request_id, vr['rule_name'], vr['passed'], vr['severity'], vr['message'], status_val)
            )
            if vr['severity'] == 'error' and not vr['passed']:
                has_errors = True
        
        write_audit(request_id, "Validation Agent", "Validate", f"{len(generated_files)} files", val_summary)
        execute_write("UPDATE generation_requests SET status='validated' WHERE id=%s", (request_id,))
        
        # Pipeline pauses here for Tech Lead review
        update_job_status(job_id, 'completed', 'Finished', 'Pipeline paused for Tech Lead review')
        
    except Exception as e:
        logger.error(f"Pipeline error: {traceback.format_exc()}")
        update_job_status(job_id, 'failed', 'Error', f"Exception: {str(e)}")
        write_audit(request_id, "Orchestrator", "Execute", "Pipeline", "Failed", str(e))

def run_packaging(request_id, job_id=None):
    try:
        if job_id:
            update_job_status(job_id, 'running', 'Packaging', 'Marking as packaged (in DB)')
        
        zip_path = "virtual/db_stored.zip"
                    
        execute_write("DELETE FROM packages WHERE request_id=%s", (request_id,))
        execute_write(
            "INSERT INTO packages (request_id, zip_path, validation_summary) VALUES (%s, %s, %s)",
            (request_id, zip_path, "Approved and Packaged by Tech Lead")
        )
        execute_write("UPDATE generation_requests SET status='packaged' WHERE id=%s", (request_id,))
        write_audit(request_id, "Packaging Agent", "Zip", "Valid files", f"Created {zip_path}")
        
        if job_id:
            update_job_status(job_id, 'completed', 'Finished', 'Packaging completed successfully')
    except Exception as e:
        logger.error(f"Packaging error: {traceback.format_exc()}")
        if job_id:
            update_job_status(job_id, 'failed', 'Error', f"Exception: {str(e)}")
        write_audit(request_id, "Packaging Agent", "Zip", "Valid files", "Failed", str(e))

def start_pipeline_thread(request_id, draft_mode=False):
    job_id = execute_write("INSERT INTO pipeline_jobs (request_id) VALUES (%s)", (request_id,))
    t = threading.Thread(target=run_pipeline, args=(request_id, job_id, draft_mode))
    t.start()
    return job_id

def start_packaging_thread(request_id):
    job_id = execute_write("INSERT INTO pipeline_jobs (request_id) VALUES (%s)", (request_id,))
    t = threading.Thread(target=run_packaging, args=(request_id, job_id))
    t.start()
    return job_id
