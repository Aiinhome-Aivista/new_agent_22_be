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
            'Tech Lead': 'techlead',
            'Platform / DevOps Engineer': 'devops'
        }
        
        # Define RBAC mappings
        role_id = system_role_map.get(raw_role, 'developer')
        
        session_id = str(uuid.uuid4())
        
        permissions_map = {
            'developer': ['create_request', 'generate_code', 'download_package'],
            'architect': ['review_pattern', 'modify_blueprint', 'review_architecture'],
            'techlead': ['approve', 'reject', 'rework', 'validation', 'audit'],
            'devops': ['package', 'deployment', 'configuration', 'environment']
        }
        
        dashboard_map = {
            'developer': '/developer/dashboard',
            'architect': '/architect/dashboard',
            'techlead': '/techlead/dashboard',
            'devops': '/devops/dashboard'
        }
        
        menu_map = {
            'developer': [
                {'name': 'Dashboard', 'path': '/developer/dashboard', 'icon': 'ChartBarIcon'},
                {'name': 'New Request', 'path': '/request/new', 'icon': 'PlusIcon'},
                {'name': 'My Requests', 'path': '/requests', 'icon': 'FolderIcon'},
                {'name': 'Generation Progress', 'path': '/progress', 'icon': 'CpuChipIcon'},
                {'name': 'Generated Packages', 'path': '/packages', 'icon': 'CubeIcon'},
                {'name': 'Advisor Chat', 'path': '/chat', 'icon': 'ChatBubbleLeftIcon'}
            ],
            'architect': [
                {'name': 'Dashboard', 'path': '/architect/dashboard', 'icon': 'ChartBarIcon'},
                {'name': 'Pattern Review', 'path': '/review/patterns', 'icon': 'MagnifyingGlassIcon'},
                {'name': 'Blueprint Review', 'path': '/review/blueprint', 'icon': 'DocumentCheckIcon'},
                {'name': 'Architecture Standards', 'path': '/standards', 'icon': 'BuildingLibraryIcon'},
                {'name': 'Knowledge Base', 'path': '/knowledge', 'icon': 'BookOpenIcon'},
                {'name': 'Advisor Chat', 'path': '/chat', 'icon': 'ChatBubbleLeftIcon'}
            ],
            'techlead': [
                {'name': 'Dashboard', 'path': '/techlead/dashboard', 'icon': 'ChartBarIcon'},
                {'name': 'Validation Reports', 'path': '/validation', 'icon': 'ClipboardDocumentCheckIcon'},
                {'name': 'Review Queue', 'path': '/review/queue', 'icon': 'InboxIcon'},
                {'name': 'Approvals', 'path': '/approvals', 'icon': 'CheckBadgeIcon'},
                {'name': 'Audit Trail', 'path': '/audit', 'icon': 'ListBulletIcon'},
                {'name': 'Reports', 'path': '/reports', 'icon': 'DocumentChartBarIcon'}
            ],
            'devops': [
                {'name': 'Dashboard', 'path': '/devops/dashboard', 'icon': 'ChartBarIcon'},
                {'name': 'Packaging', 'path': '/packaging', 'icon': 'CubeIcon'},
                {'name': 'Environment', 'path': '/environment', 'icon': 'ServerIcon'},
                {'name': 'Configuration', 'path': '/config', 'icon': 'CogIcon'},
                {'name': 'Deployment', 'path': '/deploy', 'icon': 'RocketLaunchIcon'},
                {'name': 'CI/CD', 'path': '/cicd', 'icon': 'ArrowPathRoundedSquareIcon'},
                {'name': 'Logs', 'path': '/logs', 'icon': 'CommandLineIcon'}
            ]
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
