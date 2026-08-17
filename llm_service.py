import requests
import os
import logging
from config import LLM_API_URL, LLM_MODEL

logger = logging.getLogger(__name__)

def call_llm(prompt, stream=False):
    payload = {"model": LLM_MODEL, "prompt": prompt, "stream": stream}
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        return ""
