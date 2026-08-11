import os
import jinja2
import logging
from config import PACKAGE_OUTPUT_DIR

logger = logging.getLogger(__name__)

def generate_code(request_id, blueprint, spec, package_name, application_id):
    """
    Renders Jinja2 templates deterministically based on blueprint and spec.
    """
    out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(request_id))
    os.makedirs(out_dir, exist_ok=True)
    
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

    # Render files
    for file_info in blueprint.get("files", []):
        filename = file_info.get("filename")
        if not filename:
            continue
            
        template_name = None
        if filename.endswith("Processor.java"):
            template_name = "Processor.java.j2"
        elif filename.endswith("Handler.java"):
            template_name = "Handler.java.j2"
        elif filename.endswith("Supplier.java"):
            template_name = "Supplier.java.j2"
        elif filename == "application.yml":
            template_name = "application.yml.j2"
        elif filename == "pom.xml" or filename == "pom_snippet.xml":
            template_name = "pom_snippet.xml.j2"
            filename = "pom.xml"
        elif filename == "README.md":
            template_name = "README.md.j2"
        elif filename.endswith("Test.java"):
            template_name = "ProcessorTest.java.j2"
            
        if template_name:
            try:
                template = env.get_template(template_name)
                content = template.render(context)
                
                # Determine subfolder
                subfolder = ""
                if filename.endswith(".java"):
                    pkg_parts = package_name.split(".")
                    subfolder = os.path.join("src", "main", "java", *pkg_parts)
                    if "Test" in filename:
                        subfolder = os.path.join("src", "test", "java", *pkg_parts)

                
                full_dir = os.path.join(out_dir, subfolder)
                os.makedirs(full_dir, exist_ok=True)
                
                file_path = os.path.join(full_dir, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                    
                generated_files.append({
                    "file_name": filename,
                    "file_path": file_path,
                    "file_type": "java" if filename.endswith(".java") else ("yaml" if filename.endswith(".yml") else "md")
                })
                
                # Update status in blueprint
                file_info["status"] = "generated"
                
            except Exception as e:
                logger.error(f"Error generating {filename}: {e}")

    # Ensure README.md is always rendered on disk
    readme_path = os.path.join(out_dir, "README.md")
    if not os.path.exists(readme_path):
        try:
            template = env.get_template("README.md.j2")
            content = template.render(context)
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)
            if not any(gf['file_name'] == 'README.md' for gf in generated_files):
                generated_files.append({
                    "file_name": "README.md",
                    "file_path": readme_path,
                    "file_type": "md"
                })
        except Exception as e:
            logger.error(f"Error rendering README.md: {e}")

    return generated_files, blueprint


