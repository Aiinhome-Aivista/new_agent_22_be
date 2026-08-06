from flask import Flask, jsonify
from flask_cors import CORS
import logging
import os
import sys

# Add Controller directory to path for imports if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from Controller.requirement_controller import requirement_bp
    from Controller.pattern_controller import pattern_bp
    from Controller.blueprint_controller import blueprint_bp
    from Controller.generation_controller import generation_bp
    from Controller.validation_controller import validation_bp
    from Controller.packaging_controller import packaging_bp
    from Controller.review_controller import review_bp
    from Controller.orchestrator_controller import orchestrator_bp
    from Controller.chat_controller import chat_bp
    from Controller.audit_controller import audit_bp
    from Controller.auth_controller import auth_bp
    from Controller.dashboard_controller import dashboard_bp
except ImportError as e:
    logging.warning(f"Failed to import controllers initially (they may not exist yet): {e}")

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

try:
    app.register_blueprint(requirement_bp, url_prefix="/api/requirements")
    app.register_blueprint(pattern_bp, url_prefix="/api/patterns")
    app.register_blueprint(blueprint_bp, url_prefix="/api/blueprint")
    app.register_blueprint(generation_bp, url_prefix="/api/generate")
    app.register_blueprint(validation_bp, url_prefix="/api/validation")
    app.register_blueprint(packaging_bp, url_prefix="/api/packages")
    app.register_blueprint(review_bp, url_prefix="/api/review")
    app.register_blueprint(orchestrator_bp, url_prefix="/api/workflow")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(audit_bp, url_prefix="/api/audit")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
except NameError as e:
    logging.warning("Some blueprints were not registered because they are not yet created.")

@app.route("/api/health")
def health():
    return jsonify({"success": True, "message": "Agent 22 API is running"})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
