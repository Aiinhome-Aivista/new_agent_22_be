from flask import Blueprint, jsonify
import token_tracker

token_bp = Blueprint('tokens', __name__)

@token_bp.route('/', methods=['GET'])
def get_tokens():
    """
    Returns the current global token counts.
    """
    counts = token_tracker.get_tokens()
    return jsonify({
        "success": True,
        "data": counts
    })

@token_bp.route('/reset', methods=['POST'])
def reset_tokens():
    """
    Resets the global token counts.
    """
    token_tracker.reset_tokens()
    return jsonify({
        "success": True,
        "message": "Token counters reset to zero."
    })
