import os
import json
from llm_service import call_llm, load_prompt
import logging

logger = logging.getLogger(__name__)

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge_base')

def get_dynamic_validation_rules():
    rules_text = ""
    target_dir = os.path.join(KB_DIR, 'validation_rules')
    if os.path.exists(target_dir):
        for file in os.listdir(target_dir):
            if file.endswith('.md'):
                with open(os.path.join(target_dir, file), 'r', encoding='utf-8') as f:
                    rules_text += f"\n--- Rule File: {file} ---\n"
                    rules_text += f.read() + "\n"
    
    if not rules_text.strip():
        rules_text = "No custom rules defined. Ensure basic Java compilation and completeness."
        
    return rules_text

def validate_package(request_id, application_id, package_dir, files_manifest, spec):
    """
    Runs dynamic validation rules against the generated package using LLM.
    """
    rules_text = get_dynamic_validation_rules()
    
    prompt = load_prompt(
        "dynamic_validation_prompt",
        validation_rules=rules_text,
        spec_json=json.dumps(spec, default=str),
        files_manifest=json.dumps(files_manifest, default=str)
    )
    
    response_text = call_llm(prompt)
    
    results = []
    try:
        results = json.loads(response_text)
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

