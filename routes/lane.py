"""
routes/lane.py
-----------------
Lane Analysis tab endpoint. Routes never call models directly --
this only ever calls services/lane_service.py.
"""

from flask import Blueprint, jsonify, request

from routes.workspace import resolve_workspace_path
from services import lane_service
from utils.file_utils import get_media_type

lane_bp = Blueprint("lane", __name__)


@lane_bp.route("/api/analyze/lane", methods=["POST"])
def analyze_lane():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")

    if not filename:
        return jsonify({"success": False, "error": "Missing filename."}), 400

    media_path = resolve_workspace_path(filename)
    if not media_path:
        return jsonify({"success": False, "error": "Uploaded file not found. Please upload again."}), 404

    media_type = get_media_type(filename)
    result = lane_service.analyze(media_path, media_type)

    return jsonify({"success": result.get("status") == "Completed", "result": result})
