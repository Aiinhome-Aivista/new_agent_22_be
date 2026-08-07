import json
import logging
from llm_service import call_llm

logger = logging.getLogger(__name__)

def normalize_requirements(req_data):
    """
    Validates mandatory fields and uses LLM to normalize free-text hints.
    """
    if not req_data.get('application_id') or not req_data.get('package_name') or not req_data.get('source_topics'):
        raise ValueError("Missing mandatory fields: application_id, package_name, or source_topics")

    prompt = f"""
    Normalize the following Kafka application requirements into a JSON object with these exact keys:
    - source_topics (string)
    - target_topics (string)
    - consumer_group (string)
    - state_store_needed (boolean)
    - error_topic_policy (string)
    
    Requirements:
    {json.dumps(req_data, default=str)}
    
    Respond ONLY with valid JSON.
    """
    
    llm_response = call_llm(prompt)
    try:
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}') + 1
        clean_json = llm_response[start_idx:end_idx]
        normalized = json.loads(clean_json)
        return normalized
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {llm_response}")
        # Fallback to manual mapping if AI parsing fails
        return {
            "source_topics": req_data.get('source_topics', ''),
            "target_topics": req_data.get('target_topics', ''),
            "consumer_group": req_data.get('consumer_group', f"{req_data.get('application_id')}-group"),
            "state_store_needed": req_data.get('state_store_needed', False),
            "error_topic_policy": req_data.get('error_topic_policy', 'DLQ')
        }
