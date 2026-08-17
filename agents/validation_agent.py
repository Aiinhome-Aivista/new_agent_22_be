import os
import json
from llm_service import call_llm
import logging

logger = logging.getLogger(__name__)

def validate_package(request_id, application_id, package_dir, files_manifest, spec):
    """
    Runs exact rules against generated package and calls LLM for plain-English explanation.
    """
    results = []
    
    # 1. Application ID present
    results.append({
        "rule_name": "Application ID present",
        "passed": bool(application_id and application_id.strip()),
        "severity": "error" if not application_id else "info",
        "message": "Application ID is present." if application_id else "Missing Application ID."
    })
    
    # 2. Topic naming convention (lowercase, numbers, hyphens, dots, underscores)
    import re
    topic_regex = re.compile(r'^[a-zA-Z0-9-._]+$')
    topics = f"{spec.get('source_topics', '')} {spec.get('target_topics', '')}".split()
    all_valid = all(topic_regex.match(t) for t in topics if t)
    results.append({
        "rule_name": "Topic naming convention",
        "passed": all_valid,
        "severity": "error" if not all_valid else "info",
        "message": "Topics match naming convention." if all_valid else "Topics contain invalid characters."
    })
    
    # 3. No duplicate Processor classes
    processors = [f["filename"] for f in files_manifest if f["filename"].endswith("Processor.java")]
    has_duplicates = len(processors) != len(set(processors))
    results.append({
        "rule_name": "No duplicate Processor classes",
        "passed": not has_duplicates,
        "severity": "error" if has_duplicates else "info",
        "message": "No duplicate processors found." if not has_duplicates else "Duplicate processors exist."
    })
    
    # 4. Supplier exists
    suppliers = [f["filename"] for f in files_manifest if f["filename"].endswith("Supplier.java")]
    passed_supplier = len(suppliers) > 0 or len(processors) > 0
    results.append({
        "rule_name": "Supplier exists",
        "passed": passed_supplier,
        "severity": "warning" if not passed_supplier else "info",
        "message": "Supplier exists or skipped because Processor exists." if passed_supplier else "No Supplier or Processor found."
    })
    
    # 5. README exists
    readme_exists = any(f.get("filename") == "README.md" for f in files_manifest) or os.path.exists(os.path.join(package_dir, "README.md"))
    results.append({
        "rule_name": "README exists",
        "passed": readme_exists,
        "severity": "error" if not readme_exists else "info",
        "message": "README.md is present." if readme_exists else "README.md is missing."
    })
    
    # 6. YAML config complete
    yaml_exists = any(f["filename"] == "application.yml" for f in files_manifest)
    results.append({
        "rule_name": "YAML config complete",
        "passed": yaml_exists,
        "severity": "error" if not yaml_exists else "info",
        "message": "application.yml is present." if yaml_exists else "application.yml is missing."
    })
    
    # 7. JUnit test exists
    test_exists = any(f["filename"].endswith("Test.java") for f in files_manifest)
    results.append({
        "rule_name": "JUnit test exists",
        "passed": test_exists,
        "severity": "warning" if not test_exists else "info",
        "message": "At least one Test file is present." if test_exists else "No JUnit tests found."
    })
    
    # LLM summary
    summary_prompt = f"Summarize these validation results for a developer:\n{json.dumps(results, default=str)}"
    summary = call_llm(summary_prompt)
    
    return results, summary
