import json
import logging
from llm_service import call_llm

logger = logging.getLogger(__name__)

def generate_blueprint(spec, patterns):
    """
    Calls LLM with spec + patterns to produce file manifest and design.
    """
    prompt = f"""
    Design a Kafka Streams application based on these specs:
    {json.dumps(spec, default=str)}
    
    Consider these retrieved patterns/standards:
    {json.dumps(patterns, default=str)}
    
    Produce a JSON response with exactly this structure:
    {{
      "files": [
        {{ "filename": "OrderProcessor.java", "purpose": "Consumes input", "generated": false, "status": "planned" }}
      ],
      "class_design": "Detailed string about classes and methods...",
      "rationale": "Why this design was chosen...",
      "alternative_designs": ["Alternative option 1...", "Alternative option 2..."],
      "assumptions": ["Assumed state store because...", "Assumed exact once semantics..."]
    }}
    
    Ensure you include at minimum a Processor, a Handler, and an application.yml.
    Respond ONLY with valid JSON.
    """
    
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
            "assumptions": ["Fallback design assumption"]
        }
