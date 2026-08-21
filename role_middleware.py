from functools import wraps
from flask import request, jsonify

def requires_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = request.headers.get('X-User-Role')
            
            # Map the database roles to the internal ID if needed, 
            # or just use the ID (developer, architect, techlead) directly
            # For this demo, let's assume the frontend passes the internal ID (e.g. 'developer') in the header.
            if not user_role or user_role not in roles:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized', 
                    'message': f'You do not have permission to access this resource. Required roles: {roles}'
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
