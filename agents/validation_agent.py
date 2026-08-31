import os
import json
from llm_service import call_llm, load_prompt
import logging
from db import execute_query

logger = logging.getLogger(__name__)

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge_base')

def get_dynamic_validation_rules(track_id=None):
    rules_text = ""
    
    # Query validation rules from DB for this track (or global)
    if track_id is not None:
        db_rules = execute_query(
            "SELECT title, description FROM architecture_standards WHERE folder = 'validation_rules' AND (track_id = %s OR track_id IS NULL)",
            (track_id,)
        )
    else:
        db_rules = execute_query(
            "SELECT title, description FROM architecture_standards WHERE folder = 'validation_rules'"
        )

    if db_rules:
        for rule in db_rules:
            rules_text += f"\n--- Rule: {rule.get('title')} ---\n"
            rules_text += (rule.get('description') or "") + "\n"
    
    if not rules_text.strip():
        rules_text = "No custom rules defined. Ensure basic Java compilation and completeness."
        
    return rules_text

def validate_package(request_id, application_id, package_dir, files_manifest, spec, track_id=None):
    """
    Runs dynamic validation rules against the generated package using LLM.
    """
    rules_text = get_dynamic_validation_rules(track_id)
    
    prompt = load_prompt(
        "dynamic_validation_prompt",
        validation_rules=rules_text,
        spec_json=json.dumps(spec, default=str),
        files_manifest=json.dumps(files_manifest, default=str)
    )
    
    response_text = call_llm(prompt)
    
    results = []
    try:
        import re
        response_text = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', response_text)
        results = json.loads(response_text, strict=False)
        if not isinstance(results, list):
            results = [results]
    except Exception as e:
        logger.error(f"Failed to parse LLM validation response: {e}")
        # Fallback error result
        results = [{
            "rule_name": "Validation Execution",
            "passed": False,
            "severity": "error",
            "message": "The AI auditor failed to return a valid JSON response."
        }]
    
    # Generate LLM summary based on results
    summary_prompt = load_prompt("validation_summary_prompt", results_json=json.dumps(results, default=str))
    summary = call_llm(summary_prompt)
    
    return results, summary

