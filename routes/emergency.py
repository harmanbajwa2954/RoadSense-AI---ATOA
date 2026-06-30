"""
routes/emergency.py
----------------------
Emergency Vehicle Analysis tab endpoint.
"""

from flask import Blueprint, jsonify, request

from routes.workspace import resolve_workspace_path
from services import emergency_service
from utils.file_utils import get_media_type

emergency_bp = Blueprint("emergency", __name__)


@emergency_bp.route("/api/analyze/emergency", methods=["POST"])
def analyze_emergency():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")

    if not filename:
        return jsonify({"success": False, "error": "Missing filename."}), 400

    media_path = resolve_workspace_path(filename)
    if not media_path:
        return jsonify({"success": False, "error": "Uploaded file not found. Please upload again."}), 404

    media_type = get_media_type(filename)
    result = emergency_service.analyze(media_path, media_type)

    return jsonify({"success": result.get("status") == "Completed", "result": result})
