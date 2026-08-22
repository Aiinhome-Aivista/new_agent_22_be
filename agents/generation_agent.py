import os
import jinja2
import logging
from config import PACKAGE_OUTPUT_DIR
from llm_service import call_llm, load_prompt
import re
import concurrent.futures

logger = logging.getLogger(__name__)

def generate_code(request_id, blueprint, spec, package_name, application_id):
    """
    Renders Jinja2 templates deterministically based on blueprint and spec.
    """
    out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(request_id))
    # Removed physical directory creation since code paths are virtual
    
    template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    
    generated_files = []
    
    # Context for templates
    context = {
        "package_name": package_name,
        "application_id": application_id,
        "source_topics": spec.get("source_topics", ""),
        "target_topics": spec.get("target_topics", ""),
        "consumer_group": spec.get("consumer_group", ""),
        "state_store_needed": spec.get("state_store_needed", False),
        "error_topic_policy": spec.get("error_topic_policy", ""),
        "processor_class_name": "DefaultProcessor",
        "handler_class_name": "DefaultHandler",
        "supplier_class_name": "DefaultSupplier"
    }
    
    # Try to extract class names from blueprint files
    for f in blueprint.get("files", []):
        fname = f.get("filename", "")
        if fname.endswith("Processor.java"):
            context["processor_class_name"] = fname.replace(".java", "")
        elif fname.endswith("Handler.java"):
            context["handler_class_name"] = fname.replace(".java", "")
        elif fname.endswith("Supplier.java"):
            context["supplier_class_name"] = fname.replace(".java", "")
            
    # Ensure README.md is always included in generated files
    filenames = [f.get("filename", "") for f in blueprint.get("files", [])]
    if "README.md" not in filenames:
        blueprint.get("files", []).append({"filename": "README.md", "purpose": "Documentation for microservice", "status": "planned"})

    # Render files concurrently
    def process_file(file_info):
        filename = file_info.get("filename")
        if not filename:
            return None
            
        template_name = None
        if filename.endswith("Processor.java"):
            template_name = "Processor.java.j2"
        elif filename.endswith("Handler.java"):
            template_name = "Handler.java.j2"
        elif filename.endswith("Supplier.java"):
            template_name = "Supplier.java.j2"
        elif filename.endswith("Application.java") or filename == "Application.java":
            template_name = "Application.java.j2"
        elif filename.endswith("Config.java"):
            template_name = "Config.java.j2"
        elif filename.endswith("Model.java") or filename.endswith("DTO.java"):
            template_name = "Model.java.j2"
        elif filename == "application.yml":
            template_name = "application.yml.j2"
        elif filename == "pom.xml" or filename == "pom_snippet.xml":
            template_name = "pom_snippet.xml.j2"
            filename = "pom.xml"
        elif filename == "README.md":
            template_name = "README.md.j2"
        elif filename.endswith("Test.java"):
            template_name = "ProcessorTest.java.j2"
            
        content = ""
        if template_name:
            try:
                template = env.get_template(template_name)
                content = template.render(context)
            except Exception as e:
                logger.error(f"Error rendering template {template_name}: {e}")
                
        # Enhance code with LLM or generate from scratch if no template
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Generating/Enhancing {filename} with LLM (Attempt {attempt+1}/{max_retries})...")
                
                if content:
                    prompt = load_prompt(
                        "generation_prompt",
                        filename=filename,
                        purpose=file_info.get("purpose", ""),
                        class_design=blueprint.get("class_design", ""),
                        mermaid_diagram=blueprint.get("mermaid_diagram", ""),
                        skeleton_code=content
                    )
                else:
                    prompt = f"You are a Java Spring Boot Kafka Architect.\nGenerate the full code for {filename}.\nPurpose: {file_info.get('purpose', '')}\nOverall Class Design:\n{blueprint.get('class_design', '')}\nPackage: {package_name}\n\nRespond ONLY with the raw source code wrapped in ```java ... ``` blocks. Do not include markdown headers or explanations."
                    
                llm_code = call_llm(prompt)
                if llm_code and llm_code.strip():
                    match = re.search(r"```(?:\w+)?\n(.*?)```", llm_code, re.DOTALL)
                    if match:
                        content = match.group(1).strip()
                    else:
                        content = llm_code.strip()
                        
                if content:
                    break
            except Exception as e:
                logger.error(f"Failed to generate {filename} with LLM: {e}")
                
        if not content:
            logger.error(f"Failed to generate {filename} after {max_retries} attempts.")
            return None
                
        # Determine subfolder
        subfolder = ""
        if filename.endswith(".java"):
            pkg_parts = package_name.split(".")
            subfolder = os.path.join("src", "main", "java", *pkg_parts)
            if "Test" in filename:
                subfolder = os.path.join("src", "test", "java", *pkg_parts)
        elif filename.endswith(".yml") or filename.endswith(".yaml") or filename.endswith(".properties"):
            subfolder = os.path.join("src", "main", "resources")

        
        full_dir = os.path.join(out_dir, subfolder)
        
        # virtual path for reference, no actual disk writing
        file_path = os.path.join(full_dir, filename).replace('\\', '/')
            
        # Update status in blueprint
        file_info["status"] = "generated"
        
        return {
            "file_name": filename,
            "file_path": file_path,
            "file_type": "java" if filename.endswith(".java") else ("yaml" if filename.endswith(".yml") else "md"),
            "file_content": content
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(process_file, blueprint.get("files", []))
        
    for res in results:
        if res:
            generated_files.append(res)

    # Ensure README.md is always included in the results
    readme_path = os.path.join(out_dir, "README.md").replace('\\', '/')
    if not any(gf['file_name'] == 'README.md' for gf in generated_files):
        try:
            template = env.get_template("README.md.j2")
            content = template.render(context)
            generated_files.append({
                "file_name": "README.md",
                "file_path": readme_path,
                "file_type": "md",
                "file_content": content
            })
        except Exception as e:
            logger.error(f"Error rendering README.md: {e}")

    return generated_files, blueprint


