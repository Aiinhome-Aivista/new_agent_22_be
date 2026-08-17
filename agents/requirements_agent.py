import json
import logging
from llm_service import call_llm

logger = logging.getLogger(__name__)

def analyze_conversational_intake(messages, language="Java Kafka", files=None):
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

    prompt = f"""
    You are an expert AI software architect. You are chatting with a developer to gather requirements for a new project.
    Language Target: {language}
    {files_str}
    
    Conversation History:
    {history_str}
    
    Your task:
    Evaluate if you have enough information to generate a basic Software Blueprint (which requires at least a general idea of the project's purpose and architecture).
    
    If you DO NOT have enough information (e.g. the user just said "hi" or the prompt is too vague), you must ask a clarifying question.
    If you DO have enough information, you must extract the requirements.
    
    Respond ONLY with a valid JSON object matching exactly one of these two structures:
    
    Structure 1 (Need more info):
    {{
        "status": "more_info",
        "question": "Your clarifying question here..."
    }}
    
    Structure 2 (Complete):
    {{
        "status": "complete",
        "requirements": {{
            "request_name": "Short descriptive name",
            "application_id": "com.company.app",
            "package_name": "com.company.app",
            "source_topics": "comma separated source topics",
            "target_topics": "comma separated target topics or empty",
            "consumer_group": "consumer group name",
            "state_store_needed": true or false,
            "error_topic_policy": "DLQ, IGNORE, or RETRY"
        }}
    }}
    
    Do not include any markdown formatting like ```json. Respond ONLY with the raw JSON.
    """
    
    llm_response = call_llm(prompt)
    try:
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}') + 1
        clean_json = llm_response[start_idx:end_idx]
        return json.loads(clean_json)
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
    prompt = f"""
    You are an AI architect. The user is requesting a new project based on the following input:
    Language Selected: {req_data.get('language', 'Unknown')}
    User Prompt: {req_data.get('prompt', '')}
    Attached Files: {req_data.get('attached_files', [])}
    
    Extract the following details and return ONLY a valid JSON object with exactly these keys:
    - request_name (string: a short, descriptive name for the project)
    - application_id (string: a java/app style id, e.g., com.company.service)
    - package_name (string: standard package name, e.g., com.company.service)
    - source_topics (string: comma separated list of kafka source topics)
    - target_topics (string: comma separated list of kafka target topics, or empty)
    - consumer_group (string: kafka consumer group name)
    - state_store_needed (boolean: true if stateful processing is mentioned)
    - error_topic_policy (string: DLQ, IGNORE, or RETRY)
    
    If any detail is not explicitly mentioned, make a reasonable guess based on context.
    Respond ONLY with valid JSON. Do not include markdown formatting like ```json.
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
