from flask import Blueprint, request, jsonify
from db import get_connection

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
        return jsonify({
            "success": True, 
            "user": user,
            "token": f"mock-jwt-token-{user['id']}"
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
