import json
import logging
from db import execute_query, execute_write
from llm_service import call_llm, load_prompt
from agents.validation_agent import get_dynamic_validation_rules
from config import PACKAGE_OUTPUT_DIR
import os

logger = logging.getLogger(__name__)

def fix_package(request_id, rule_name, message):
    """
    Asks the LLM to fix specific generated files to pass a failed validation rule.
    Updates the files in the DB and on disk.
    """
    # 1. Get current files
    gen_files = execute_query("SELECT file_name, file_path, file_content FROM generated_files WHERE request_id=%s", (request_id,))
    if not gen_files:
        return False
        
    files_json = json.dumps([{"file_name": f["file_name"], "file_content": f["file_content"]} for f in gen_files])
    
    # Fetch track_id for this request
    req = execute_query("SELECT track_id FROM generation_requests WHERE id=%s", (request_id,))
    track_id = req[0]['track_id'] if req else None

    # 2. Get the full validation rules context
    rules_text = get_dynamic_validation_rules(track_id)
    
    # Get Blueprint context
    bp = execute_query("SELECT file_manifest, class_design FROM blueprints WHERE request_id=%s ORDER BY id DESC LIMIT 1", (request_id,))
    blueprint_text = ""
    if bp:
        blueprint_text = f"File Manifest:\n{bp[0].get('file_manifest', '')}\n\nClass Design:\n{bp[0].get('class_design', '')}"
        
    # 3. Call LLM to fix
    prompt = load_prompt("auto_fix_prompt", rule_name=rule_name, message=message, files_json=files_json, validation_rules=rules_text, blueprint=blueprint_text)
    
    logger.info(f"Requesting auto-fix for rule: {rule_name}")
    response = call_llm(prompt, options={"temperature": 0.3})
    
    if not response:
        logger.error("LLM returned empty response for auto-fix")
        return False
        
    try:
        import re
        # Parse XML <fix> tags from LLM response
        file_blocks = re.findall(
            r'<fix[^>]*file_name=["\']([^"\']+)["\'][^>]*>.*?<content>(.*?)</content>\s*</fix>',
            response, re.DOTALL
        )
        
        if not file_blocks:
            logger.info("LLM did not return any files to fix.")
            return False
            
        # Update files in DB and on disk
        changed_any = False
        for fname, fcontent in file_blocks:
            fname = fname.strip()
            fcontent = fcontent.strip()
            
            if not fname or not fcontent:
                continue
                
            # Find matching file in original set
            target = next((f for f in gen_files if f["file_name"] == fname), None)
            if target:
                # Update DB
                execute_write("UPDATE generated_files SET file_content=%s WHERE request_id=%s AND file_name=%s", (fcontent, request_id, fname))
                
                # Update Disk
                disk_path = target["file_path"]
                if os.path.exists(os.path.dirname(disk_path)):
                    with open(disk_path, 'w', encoding='utf-8') as f:
                        f.write(fcontent)
                        
                changed_any = True
                logger.info(f"Auto-fixed file: {fname}")
                
        return changed_any
        
    except Exception as e:
        logger.error(f"Failed to parse or apply auto-fix response: {e}\nResponse was: {response}")
        return False
