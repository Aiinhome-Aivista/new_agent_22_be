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
        
        # Normalize alternative LLM keys
        if not blueprint.get("class_design"):
            blueprint["class_design"] = blueprint.get("classDesign", blueprint.get("design", ""))
            
        if not blueprint.get("rationale"):
            blueprint["rationale"] = blueprint.get("generated_rationale", blueprint.get("architecture_rationale", ""))
            
        if not blueprint.get("mermaid_diagram"):
            blueprint["mermaid_diagram"] = blueprint.get("mermaidDiagram", blueprint.get("diagram", ""))
            
        # If still empty, try to extract from outside the JSON
        if not blueprint.get("class_design"):
            import re
            cd_match = re.search(r'(?i)(?:class design|design):?\s*\n+(.*?)(?:\n\s*\n|(?=rationale)|(?=mermaid)|$)', llm_response, re.DOTALL)
            if cd_match: blueprint["class_design"] = cd_match.group(1).strip()
            
        if not blueprint.get("rationale"):
            rat_match = re.search(r'(?i)(?:rationale|generated rationale):?\s*\n+(.*?)(?:\n\s*\n|(?=mermaid)|$)', llm_response, re.DOTALL)
            if rat_match: blueprint["rationale"] = rat_match.group(1).strip()
            
        if not blueprint.get("mermaid_diagram"):
            mer_match = re.search(r'```mermaid\s*(.*?)\s*```', llm_response, re.DOTALL)
            if mer_match: blueprint["mermaid_diagram"] = mer_match.group(1).strip()
        
        # Clean up mermaid diagram if it contains markdown backticks
        if "mermaid_diagram" in blueprint and blueprint["mermaid_diagram"]:
            diagram = blueprint["mermaid_diagram"]
            if diagram.startswith("```mermaid"):
                diagram = diagram.replace("```mermaid", "", 1)
            elif diagram.startswith("```"):
                diagram = diagram.replace("```", "", 1)
            if diagram.endswith("```"):
                diagram = diagram[:-3]
            blueprint["mermaid_diagram"] = diagram.strip()
            
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
