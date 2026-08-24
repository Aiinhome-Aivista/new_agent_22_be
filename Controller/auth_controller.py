from flask import Blueprint, request, jsonify
from db import get_connection, execute_query
import uuid
import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400
        
    users = execute_query("SELECT id, name, role, email, password, description FROM users WHERE email = %s", (email,))
    user = users[0] if users else None
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        del user['password'] # Remove encrypted password before returning to client
        
        raw_role = user['role'].strip()
        system_role_map = {
            'Developer': 'developer',
            'Solution Architect': 'architect',
            'Tech Lead': 'techlead'
        }
        
        # Define RBAC mappings
        role_id = system_role_map.get(raw_role, 'developer')
        
        session_id = str(uuid.uuid4())
        
        permissions_map = {
            'developer': ['create_request', 'generate_code', 'download_package'],
            'architect': ['review_pattern', 'modify_blueprint', 'review_architecture'],
            'techlead': ['approve', 'reject', 'rework', 'validation', 'audit']
        }
        
        dashboard_map = {
            'developer': '/dashboard-overview',
            'architect': '/dashboard-overview',
            'techlead': '/dashboard-overview'
        }
        
        directory_menu = [
            {'name': 'Dashboard', 'path': '/dashboard-overview', 'icon': 'ChartBarIcon'},
            {'name': 'Projects', 'path': '/projects', 'icon': 'FolderIcon'}
        ]
        
        menu_map = {
            'developer': directory_menu,
            'architect': directory_menu,
            'techlead': directory_menu
        }
        
        payload = {
            "session_id": session_id,
            "login_time": None,
            "user": user,
            "role": role_id,
            "permissions": permissions_map.get(role_id, []),
            "dashboard": dashboard_map.get(role_id, '/'),
            "menu": menu_map.get(role_id, [])
        }
        
        return jsonify({
            "success": True, 
            **payload
        })
    else:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401
        
@auth_bp.route('/personas', methods=['GET'])
def get_personas():
    users = execute_query("SELECT email, role, name, description FROM users")
    
    return jsonify({"success": True, "data": users})
