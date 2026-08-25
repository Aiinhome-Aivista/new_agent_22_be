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
    
    # 3. Call LLM to fix
    prompt = load_prompt("auto_fix_prompt", rule_name=rule_name, message=message, files_json=files_json, validation_rules=rules_text)
    
    logger.info(f"Requesting auto-fix for rule: {rule_name}")
    response = call_llm(prompt)
    
    if not response:
        logger.error("LLM returned empty response for auto-fix")
        return False
        
    try:
        # Extract JSON array from markdown response if present
        import re
        match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            response = match.group(1)
        elif response.startswith("```"):
            response = response.replace("```", "").strip()
            
        try:
            fixed_files = json.loads(response, strict=False)
        except json.JSONDecodeError as je:
            logger.warning(f"Failed to parse JSON directly, attempting basic repair. Error: {je}")
            # If response is truncated, we can't easily fix without a library, but let's try 
            # to replace literal newlines with \\n just in case strict=False didn't catch everything or it was truncated
            try:
                # Basic escaping of literal newlines within quotes could be complex. 
                # Let's just try to close the array if it's missing.
                if not response.rstrip().endswith("]"):
                    if not response.rstrip().endswith("}"):
                        response += '"}]'
                    else:
                        response += "]"
                fixed_files = json.loads(response, strict=False)
            except Exception as e2:
                logger.error(f"Failed to repair JSON: {e2}")
                raise je
        if not isinstance(fixed_files, list) or len(fixed_files) == 0:
            logger.info("LLM did not return any files to fix.")
            return False
            
        # 3. Update files in DB and on disk
        changed_any = False
        for fixed_file in fixed_files:
            fname = fixed_file.get("file_name")
            fcontent = fixed_file.get("file_content")
            
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
