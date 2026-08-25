import json
import logging
from llm_service import call_llm, load_prompt

logger = logging.getLogger(__name__)

def generate_blueprint(spec, patterns, existing_files=None):
    """
    Calls LLM with spec + patterns to produce file manifest and design.
    """
    existing_files_str = "\n".join(existing_files) if existing_files else "None"
    prompt = load_prompt("blueprint_prompt", spec_json=json.dumps(spec, default=str), patterns_json=json.dumps(patterns, default=str), existing_files=existing_files_str)
    
    llm_response = call_llm(prompt)
    try:
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}') + 1
        clean_json = llm_response[start_idx:end_idx]
        blueprint = json.loads(clean_json)
        return blueprint
    except Exception as e:
        logger.error(f"Failed to parse LLM blueprint response: {e}")
        # Fallback blueprint
        return {
            "files": [
                { "filename": "DefaultProcessor.java", "purpose": "Main topology", "generated": False, "status": "planned" },
                { "filename": "DefaultHandler.java", "purpose": "Business logic", "generated": False, "status": "planned" },
                { "filename": "application.yml", "purpose": "Configuration", "generated": False, "status": "planned" },
                { "filename": "README.md", "purpose": "Documentation", "generated": False, "status": "planned" },
                { "filename": "DefaultProcessorTest.java", "purpose": "Tests", "generated": False, "status": "planned" }
            ],
            "class_design": "Default simple layout",
            "rationale": "Fallback due to LLM parsing error",
            "alternative_designs": ["No alternatives due to error"],
            "assumptions": ["Fallback design assumption"],
            "mermaid_diagram": "graph TD;\n  A[Input] --> B[Processor];\n  B --> C[Output];"
        }
