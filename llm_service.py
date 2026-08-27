import requests
import os
import logging
from config import LLM_API_URL, LLM_MODEL

logger = logging.getLogger(__name__)

def load_prompt(prompt_name, **kwargs):
    try:
        from db import execute_query, execute_write
        # Try fetching from DB first
        db_prompts = execute_query("SELECT prompt_text FROM system_prompts WHERE prompt_name=%s", (prompt_name,))
        if db_prompts and len(db_prompts) > 0:
            template = db_prompts[0]['prompt_text']
            return template.format(**kwargs)
            
        # Fallback to local .txt file
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", f"{prompt_name}.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
            
        # Automatically seed the database for future runs
        execute_write(
            "INSERT INTO system_prompts (prompt_name, prompt_text) VALUES (%s, %s)",
            (prompt_name, template)
        )
        return template.format(**kwargs)
    except Exception as e:
        logger.error(f"Error loading prompt {prompt_name}: {e}")
        return ""

def call_llm(prompt, stream=False, images=None):
    payload = {"model": LLM_MODEL, "prompt": prompt, "stream": stream}
    if images:
        payload["images"] = images
        
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=600)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        return ""
