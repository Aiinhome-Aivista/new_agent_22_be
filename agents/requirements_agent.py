import json
import logging
from llm_service import call_llm, load_prompt

logger = logging.getLogger(__name__)

def analyze_conversational_intake(messages, language="Java Kafka", files=None, images=None):
    """
    Analyzes the conversation history to determine if enough requirements have been gathered.
    If not, it asks a clarifying question. If yes, it extracts the requirements.
    """
    files_str = f"Attached Files: {files}\n" if files else ""
    
    # Format chat history
    history_str = ""
    for msg in messages:
        role = "User" if msg.get("role") == "user" else "Agent"
        history_str += f"{role}: {msg.get('text')}\n"

    prompt = load_prompt("analyze_conversation_prompt", language=language, files_str=files_str, history_str=history_str)
    
    llm_response = call_llm(prompt, images=images)
    try:
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}') + 1
        clean_json = llm_response[start_idx:end_idx]
        import re
        clean_json = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', clean_json)
        return json.loads(clean_json, strict=False)
    except Exception as e:
        logger.error(f"Failed to parse conversational LLM response: {llm_response}")
        return {
            "status": "more_info",
            "question": "I'm having trouble understanding. Could you please provide more details about your project?"
        }

def normalize_requirements(req_data):
    """
    Uses LLM to normalize free-text hints into structured requirements.
    """
    prompt = load_prompt("normalize_requirements_prompt", language=req_data.get('language', 'Unknown'), user_prompt=req_data.get('prompt', ''), attached_files=req_data.get('attached_files', []))
    
    llm_response = call_llm(prompt, images=req_data.get('attached_images', []))
    try:
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}') + 1
        clean_json = llm_response[start_idx:end_idx]
        import re
        clean_json = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', clean_json)
        normalized = json.loads(clean_json, strict=False)
        return normalized
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {llm_response}")
        # Fallback if AI parsing fails
        return {
            "request_name": "NLP Extracted Project",
            "application_id": "com.generated.app",
            "package_name": "com.generated.app",
            "source_topics": "default.source",
            "target_topics": "",
            "consumer_group": "default-group",
            "state_store_needed": False,
            "error_topic_policy": "DLQ"
        }
