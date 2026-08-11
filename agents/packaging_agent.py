import json
import logging
from llm_service import call_llm

logger = logging.getLogger(__name__)

def generate_packaging_scripts(spec, env_config, java_files):
    """
    Calls LLM to produce pom.xml, Dockerfile, and deployment.yaml based on environment config and code.
    """
    prompt = f"""
    You are a DevOps AI Agent. Your task is to generate packaging and deployment scripts for a Kafka Streams application.
    
    Application Spec:
    {json.dumps(spec, default=str)}
    
    Target Environment Configuration:
    {json.dumps(env_config, default=str)}
    
    Generated Java Files manifest:
    {json.dumps([f['file_name'] for f in java_files])}
    
    Produce a JSON response with exactly this structure:
    {{
      "pom_xml": "<string content of a valid Maven pom.xml>",
      "dockerfile": "<string content of a valid Dockerfile using a Java runtime>",
      "deployment_yaml": "<string content of a valid Kubernetes deployment and service yaml>"
    }}
    
    Rules:
    - Ensure the pom.xml has the correct groupId based on the package_name, and artifactId based on the application_id.
    - Ensure Dockerfile exposes the typical prometheus/health port (e.g. 8080).
    - Ensure deployment.yaml uses the docker_registry and namespace from the environment configuration.
    - Respond ONLY with valid JSON.
    """
    
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
