from flask import Blueprint, request, jsonify
from db import get_connection
import uuid

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400
        
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, name, role, email, description, icon, color FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if user:
        # Define RBAC mappings
        role_id = user['id']
        
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
            'techlead': '/reviewer/dashboard',
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
                {'name': 'Dashboard', 'path': '/reviewer/dashboard', 'icon': 'ChartBarIcon'},
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
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT email, password, icon, color, role, name FROM users")
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({"success": True, "data": users})
