import json
import logging
from llm_service import call_llm, load_prompt

logger = logging.getLogger(__name__)

from config import MIN_BLUEPRINT_ACCURACY, MAX_AUTO_FIX_RETRIES
from agents.blueprint_validation_agent import evaluate_blueprint

def _generate_blueprint_single_pass(spec, patterns, existing_files=None, comments=""):
    """
    Calls LLM with spec + patterns to produce file manifest and design.
    """
    existing_files_str = "\n".join(existing_files) if existing_files else "None"
    
    comments_section = ""
    if comments and comments.strip():
        comments_section = f"\nREWORK FEEDBACK (If applicable):\nThe following feedback has been provided on the previous iteration of this design. You MUST incorporate this feedback into your updated architecture and class design:\n{comments.strip()}\n"
        
    prompt = load_prompt("blueprint_prompt", spec_json=json.dumps(spec, default=str), patterns_json=json.dumps(patterns, default=str), existing_files=existing_files_str, comments=comments_section)
    
    llm_response = call_llm(prompt)
    try:
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}') + 1
        clean_json = llm_response[start_idx:end_idx]
        import re
        clean_json = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', clean_json)
        blueprint = json.loads(clean_json, strict=False)
        
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

def generate_blueprint(spec, patterns, existing_files=None, comments=""):
    """
    Generates blueprint and auto-validates against track standards up to MAX_AUTO_FIX_RETRIES times.
    """
    retries = 0
    current_comments = comments
    
    best_blueprint = None
    best_score = -1
    best_feedback = ""

    while retries <= MAX_AUTO_FIX_RETRIES:
        if retries == 0:
            logger.info("Generating initial blueprint...")
        else:
            logger.info(f"Regenerating blueprint (Auto-fix Attempt {retries}/{MAX_AUTO_FIX_RETRIES})")
            
        blueprint = _generate_blueprint_single_pass(spec, patterns, existing_files, current_comments)
        
        # Evaluate
        eval_result = evaluate_blueprint(blueprint, spec, patterns)
        accuracy = eval_result.get("accuracy_score", 0)
        reasons = eval_result.get("reasons", [])
        
        logger.info(f"Blueprint validation accuracy: {accuracy}%")
        
        blueprint["accuracy_score"] = accuracy
        blueprint["validation_feedback"] = "\n".join(reasons) if reasons else ""

        # Track the best blueprint so far
        if accuracy > best_score:
            best_score = accuracy
            best_blueprint = blueprint
            best_feedback = blueprint["validation_feedback"]

        if accuracy >= MIN_BLUEPRINT_ACCURACY:
            logger.info("Blueprint met accuracy threshold.")
            break
            
        # Prepare for retry
        retries += 1
        if retries <= MAX_AUTO_FIX_RETRIES:
            logger.warning(f"Blueprint accuracy ({accuracy}%) below threshold ({MIN_BLUEPRINT_ACCURACY}%). Auto-fixing...")
            
            # Combine original comments with new validation feedback
            additional_feedback = "\n".join(reasons)
            current_comments = comments + "\n\nAUTOMATED VALIDATION FEEDBACK (Fix these issues):\n" + additional_feedback
        else:
            logger.warning(f"Max auto-fix retries reached. Returning best effort blueprint with {best_score}% accuracy.")
            
    best_blueprint["accuracy_score"] = best_score
    best_blueprint["validation_feedback"] = best_feedback
    
    return best_blueprint
