from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
import json

env_config_bp = Blueprint('env_config', __name__)

@env_config_bp.route('/', methods=['GET'])
def get_all_configs():
    configs = execute_query("SELECT id, env_name, config_json, created_at, updated_at FROM environment_configs ORDER BY env_name")
    
    # Parse JSON strings to objects for the frontend
    for config in configs:
        try:
            config['config_json'] = json.loads(config['config_json'])
        except Exception:
            config['config_json'] = {}
            
    return jsonify({"success": True, "data": configs})

@env_config_bp.route('/<env_name>', methods=['GET'])
def get_config(env_name):
    configs = execute_query("SELECT config_json FROM environment_configs WHERE env_name = %s", (env_name,))
    if not configs:
        return jsonify({"success": False, "message": "Environment not found"}), 404
        
    try:
        config_obj = json.loads(configs[0]['config_json'])
    except Exception:
        config_obj = {}
        
    return jsonify({"success": True, "data": config_obj})

@env_config_bp.route('/<env_name>', methods=['PUT'])
def update_config(env_name):
    data = request.json
    
    if not data:
        return jsonify({"success": False, "message": "Configuration data required"}), 400
        
    config_str = json.dumps(data)
    
    # Check if exists
    existing = execute_query("SELECT id FROM environment_configs WHERE env_name = %s", (env_name,))
    
    if existing:
        execute_write("UPDATE environment_configs SET config_json = %s WHERE env_name = %s", (config_str, env_name))
    else:
        execute_write("INSERT INTO environment_configs (env_name, config_json) VALUES (%s, %s)", (env_name, config_str))
        
    return jsonify({"success": True, "message": f"{env_name} configuration updated successfully"})
