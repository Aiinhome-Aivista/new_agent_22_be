import requests
import os
import logging
import token_tracker
from config import LLM_API_URL, LLM_MODEL, MODE, MISTRAL_MODEL, MISTRAL_API_URL, MISTRAL_API_KEY

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

def call_llm(prompt, stream=False, images=None, format=None, options=None):
    if MODE.lower() == "cloud":
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": MISTRAL_MODEL,
            "messages": messages,
            "stream": stream
        }
        
        try:
            response = requests.post(MISTRAL_API_URL, json=payload, headers=headers, timeout=800)
            response.raise_for_status()
            data = response.json()
            
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            if input_tokens > 0 or output_tokens > 0:
                token_tracker.add_tokens(input_tokens, output_tokens)
                
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except Exception as e:
            logger.error(f"Error calling Mistral Cloud LLM: {e}")
            return ""
    else:
        payload = {"model": LLM_MODEL, "prompt": prompt, "stream": stream}
        if images:
            payload["images"] = images
        if format:
            payload["format"] = format
        if options:
            payload["options"] = options
            
        try:
            response = requests.post(LLM_API_URL, json=payload, timeout=800)
            response.raise_for_status()
            data = response.json()
            input_tokens = data.get("prompt_eval_count", 0)
            output_tokens = data.get("eval_count", 0)
            if input_tokens > 0 or output_tokens > 0:
                token_tracker.add_tokens(input_tokens, output_tokens)
            return data.get("response", "")
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return ""
