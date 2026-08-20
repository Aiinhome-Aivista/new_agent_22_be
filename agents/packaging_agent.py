import json
import logging
from llm_service import call_llm, load_prompt

logger = logging.getLogger(__name__)

def generate_packaging_scripts(spec, env_config, java_files):
    """
    Calls LLM to produce pom.xml, Dockerfile, and deployment.yaml based on environment config and code.
    """
    prompt = load_prompt("packaging_prompt", spec_json=json.dumps(spec, default=str), env_config_json=json.dumps(env_config, default=str), java_files_manifest=json.dumps([f['file_name'] for f in java_files]))
    
    llm_response = call_llm(prompt)
    try:
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}') + 1
        clean_json = llm_response[start_idx:end_idx]
        scripts = json.loads(clean_json)
        return scripts
    except Exception as e:
        logger.error(f"Failed to parse LLM packaging response: {e}")
        # Fallback 
        app_id = spec.get('application_id', 'kafka-app')
        pkg_name = spec.get('package_name', 'com.example')
        namespace = env_config.get('namespace', 'default')
        registry = env_config.get('docker_registry', 'docker.io')
        
        return {
            "pom_xml": f"<!-- Fallback POM -->\n<project>\n  <groupId>{pkg_name}</groupId>\n  <artifactId>{app_id}</artifactId>\n  <version>1.0.0</version>\n</project>",
            "dockerfile": "FROM openjdk:17-slim\nWORKDIR /app\nCOPY target/*.jar app.jar\nENTRYPOINT [\"java\",\"-jar\",\"/app/app.jar\"]",
            "deployment_yaml": f"apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {app_id}\n  namespace: {namespace}\nspec:\n  replicas: 1\n  template:\n    spec:\n      containers:\n      - name: app\n        image: {registry}/{app_id}:latest"
        }
