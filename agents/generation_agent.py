import os
import logging
from config import PACKAGE_OUTPUT_DIR
from llm_service import call_llm
import re

logger = logging.getLogger(__name__)

def generate_code(request_id, blueprint, spec, package_name, application_id):
    """
    Generates code using an advanced Agentic approach (Batch XML Prompting) 
    for maximum context retention, 100% accuracy, and high speed.
    """
    out_dir = os.path.join(PACKAGE_OUTPUT_DIR, str(request_id))
    generated_files = []
    
    files_to_generate = blueprint.get("files", [])
    if "README.md" not in [f.get("filename", "") for f in files_to_generate]:
        files_to_generate.append({"filename": "README.md", "purpose": "Documentation for microservice", "status": "planned"})

    # Filter out files that are marked for reuse (they are handled in the orchestrator)
    pending_files = [f for f in files_to_generate if f.get("status") != "reuse"]
    max_retries = 3
    
    # Process files in batches to optimize speed while avoiding LLM output token limits
    batch_size = 4
    
    for i in range(0, len(pending_files), batch_size):
        batch = pending_files[i:i+batch_size]
        
        for attempt in range(max_retries):
            file_descriptions = "\n".join([f"- {f['filename']}: {f.get('purpose', '')}" for f in batch])
            try:
                logger.info(f"Generating batch of {len(batch)} files (Attempt {attempt+1}/{max_retries})...")
                
                prompt = f"""You are an elite Enterprise Java Kafka Architect.
Your task is to generate production-ready code for a microservice. By generating multiple files together, you must ensure 100% consistency across classes (e.g. method signatures must match exactly).

Package: {package_name}

FILES TO GENERATE NOW:
{file_descriptions}

INTAKE CONTEXT:
Source Topics: {spec.get('source_topics', '')}
Target Topics: {spec.get('target_topics', '')}
Consumer Group: {spec.get('consumer_group', '')}
State Store Needed: {spec.get('state_store_needed', False)}

BLUEPRINT ARCHITECTURE:
{blueprint.get('class_design', '')}
{blueprint.get('mermaid_diagram', '')}

STRICT INSTRUCTIONS:
1. Provide the complete, final source code for ALL the requested files dynamically.
2. 100% Compilation Integrity: No hallucinated methods. The Processor MUST call the correct methods implemented in the Handler.
3. OUTPUT FORMAT: Wrap the content of EACH file EXACTLY in XML tags:
<file name="ExactFileName.java">
// Code here
</file>
Do NOT provide markdown wrappers (like ```java) inside or outside the XML tags. ONLY output the XML tags.
"""
                
                llm_code = call_llm(prompt)
                if not llm_code:
                    raise Exception("LLM returned empty or null response.")
                    
                # Parse XML tags
                file_blocks = re.findall(r'<file name=["\'](.*?)["\']>(.*?)</file>', llm_code, re.DOTALL)
                
                if not file_blocks:
                    raise Exception("Failed to parse <file> tags from LLM response. Format was incorrect.")
                
                generated_dict = {}
                for fname, fcontent in file_blocks:
                    # Clean any accidental markdown code block syntax
                    clean_content = re.sub(r'^```\w*\n', '', fcontent.strip())
                    clean_content = re.sub(r'```$', '', clean_content.strip()).strip()
                    generated_dict[fname.strip()] = clean_content
                    
                batch_success = True
                for file_info in batch:
                    filename = file_info.get("filename")
                    content = generated_dict.get(filename)
                    
                    if not content:
                        logger.warning(f"File {filename} was missed in the batch.")
                        batch_success = False
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
                    
                    generated_files.append({
                        "file_name": filename,
                        "file_path": file_path,
                        "file_type": "java" if filename.endswith(".java") else ("yaml" if filename.endswith(".yml") else "md"),
                        "file_content": content
                    })
                    
                # Break if we got all files in the batch, or at least some of them (to move on)
                if len(generated_dict) > 0:
                    break
                    
            except Exception as e:
                logger.error(f"Batch generation failed: {e}")
                
    return generated_files, blueprint


