import os
import logging
import json
from config import PACKAGE_OUTPUT_DIR
from llm_service import call_llm
import re
from db import execute_write

logger = logging.getLogger(__name__)

def generate_code(request_id, blueprint, spec, package_name, application_id, patterns=None):
    """
    Generates code using an advanced Agentic approach (Batch XML Prompting) 
    for maximum context retention, 100% accuracy, and high speed.
    """
    if patterns is None:
        patterns = []
    out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(request_id))
    generated_files = []
    
    files_to_generate = blueprint.get("files", [])
    if "README.md" not in [f.get("filename", "") for f in files_to_generate]:
        files_to_generate.append({"filename": "README.md", "purpose": "Documentation for microservice", "status": "planned"})

    # Filter out files that are marked for reuse (they are handled in the orchestrator)
    pending_files = [f for f in files_to_generate if f.get("status") != "reuse"]
    max_retries = 3
    
    # Process files in batches to optimize speed while avoiding LLM output token limits
    # Reduced batch size to 1 to prevent LLM timeouts when generating large POJO files
    batch_size = 1
    
    for i in range(0, len(pending_files), batch_size):
        batch = pending_files[i:i+batch_size]
        
        for attempt in range(max_retries):
            file_descriptions = "\n".join([f"- {f['filename']}: {f.get('purpose', '')}" for f in batch])
            try:
                logger.info(f"Generating batch of {len(batch)} files (Attempt {attempt+1}/{max_retries})...")
                
                patterns_json = json.dumps(patterns, default=str)
                
                from llm_service import load_prompt
                
                prompt = load_prompt(
                    "generation_prompt",
                    package_name=package_name,
                    file_descriptions=file_descriptions,
                    source_topics=spec.get('source_topics', ''),
                    target_topics=spec.get('target_topics', ''),
                    consumer_group=spec.get('consumer_group', ''),
                    state_store_needed=spec.get('state_store_needed', False),
                    developer_intake=spec.get('schema_hints', ''),
                    patterns_json=patterns_json,
                    class_design=blueprint.get('class_design', ''),
                    mermaid_diagram=blueprint.get('mermaid_diagram', '')
                )
                
                llm_code = call_llm(prompt)
                if not llm_code:
                    raise Exception("LLM returned empty or null response.")
                    
                # Parse XML tags
                file_blocks = re.findall(r'<file[^>]*name=["\']([^"\']+)["\'][^>]*>(.*?)</file>', llm_code, re.DOTALL)
                
                if not file_blocks:
                    raise Exception("Failed to parse <file> tags from LLM response. Format was incorrect.")
                
                generated_dict = {}
                for fname, fcontent in file_blocks:
                    # Clean any accidental markdown code block syntax
                    clean_content = re.sub(r'^```\w*\n', '', fcontent.strip())
                    clean_content = re.sub(r'```$', '', clean_content.strip()).strip()
                    generated_dict[fname.strip()] = clean_content
                    
                missing_in_batch = []
                for file_info in batch:
                    filename = file_info.get("filename")
                    content = generated_dict.get(filename)
                    
                    if not content:
                        logger.warning(f"File {filename} was missed in the batch.")
                        missing_in_batch.append(file_info)
                        continue
                        
                    subfolder = ""
                    if filename.endswith(".java"):
                        pkg_parts = package_name.split(".")
                        subfolder = os.path.join("src", "main", "java", *pkg_parts)
                        if "Test" in filename:
                            subfolder = os.path.join("src", "test", "java", *pkg_parts)
                    elif filename.endswith(".yml") or filename.endswith(".yaml") or filename.endswith(".properties"):
                        subfolder = os.path.join("src", "main", "resources")
                    
                    full_dir = os.path.join(out_dir, subfolder)
                    file_path = os.path.join(full_dir, filename).replace('\\', '/')
                    file_info["status"] = "generated"
                    
                    file_type = "java" if filename.endswith(".java") else ("yaml" if filename.endswith(".yml") else "md")
                    
                    generated_files.append({
                        "file_name": filename,
                        "file_path": file_path,
                        "file_type": file_type,
                        "file_content": content
                    })
                    
                    # Progressive insertion to DB with auto-analysis
                    try:
                        comments = re.findall(r'//.*|/\*.*?\*/|#.*|<!--.*?-->', content, re.DOTALL)
                        needs = any(kw in " ".join(comments).lower() for kw in ['todo', 'implement', 'logic', 'handle', 'placeholder', 'add specific'])
                        execute_write(
                            "INSERT INTO generated_files (request_id, file_name, file_path, file_type, file_content, needs_work) VALUES (%s, %s, %s, %s, %s, %s)",
                            (request_id, filename, file_path, file_type, content, needs)
                        )
                    except Exception as e:
                        logger.error(f"Failed to insert file {filename} into DB: {e}")
                    
                if not missing_in_batch:
                    break
                else:
                    batch = missing_in_batch
                    
            except Exception as e:
                logger.error(f"Batch generation failed: {e}")
                
    return generated_files, blueprint


