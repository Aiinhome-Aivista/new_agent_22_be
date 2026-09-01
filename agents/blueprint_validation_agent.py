import json
import logging
from llm_service import call_llm, load_prompt

logger = logging.getLogger(__name__)

def evaluate_blueprint(blueprint_json, spec, patterns):
    """
    Evaluates the generated blueprint against track standards and developer persona.
    Returns: {"accuracy_score": int, "reasons": list[str]}
    """
    prompt = load_prompt(
        "blueprint_validation_prompt",
        spec_json=json.dumps(spec, default=str),
        patterns_json=json.dumps(patterns, default=str),
        blueprint_json=json.dumps(blueprint_json, default=str)
    )
    
    llm_response = call_llm(prompt)
    
    try:
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}') + 1
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON object found in response")
            
        clean_json = llm_response[start_idx:end_idx]
        import re
        clean_json = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', clean_json)
        result = json.loads(clean_json, strict=False)
        
        accuracy_score = int(result.get("accuracy_score", 0))
        reasons = result.get("reasons", [])
        if not isinstance(reasons, list):
            reasons = [str(reasons)]
            
        return {
            "accuracy_score": accuracy_score,
            "reasons": reasons
        }
    except Exception as e:
        logger.error(f"Failed to parse LLM blueprint validation response: {e}\nResponse was: {llm_response}")
        # Fallback response
        return {
            "accuracy_score": 0,
            "reasons": ["Failed to evaluate the blueprint automatically due to an internal error."]
        }
