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
        {{ "filename": "<ClassName>.java", "purpose": "<description of file purpose>", "generated": false, "status": "planned" }}
      ],
      "class_design": "Detailed string describing all generated classes and their specific responsibilities...",
      "rationale": "Why this design was chosen...",
      "alternative_designs": ["Alternative option 1...", "Alternative option 2..."],
      "assumptions": ["Assumed state store because...", "Assumed exact once semantics..."],
      "mermaid_diagram": "A valid Mermaid.js flowchart (graph TD) visualizing the Kafka streams topology. Strict rules: 1. Source topics at the top. 2. Processors in the middle. 3. Processors must connect horizontally to State Stores using database shapes, e.g. Processor <-->|Queries| Store[(State Store)]. 4. Show conditional branching from the processor to target topics (e.g. Processor -->|Valid| TargetTopic and Processor -->|Error| DLQTopic). Do not just draw a straight line. Use standard mermaid formatting without markdown backticks."
    }}
    
    Ensure you include ALL necessary files for a full production-ready Spring Boot Kafka Streams microservice based on the spec. This MUST include at minimum: pom.xml, the main Application.java class, configuration classes, data models/POJOs, the Processor, the Handler, a JUnit test class (e.g. <ClassName>Test.java), and application.yml.
    Do NOT copy the generic placeholder <ClassName>. Use the actual business entity name from the spec (e.g. EmployeeProcessor, PaymentProcessor).
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
            "assumptions": ["Fallback design assumption"],
            "mermaid_diagram": "graph TD;\n  A[Input] --> B[Processor];\n  B --> C[Output];"
        }
