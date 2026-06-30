"""
routes/drowsiness.py
-----------------------
Driver Monitoring page. This page is intentionally separate from the
Analysis Workspace -- it has its own upload section and runs ONLY the
Driver Drowsiness model.
"""

from flask import Blueprint, jsonify, render_template, request

from services import drowsiness_service
from utils.file_utils import save_module_upload

drowsiness_bp = Blueprint("drowsiness", __name__)


@drowsiness_bp.route("/driver-monitoring")
def driver_monitoring_page():
    return render_template("drowsiness.html", active_page="drowsiness")


@drowsiness_bp.route("/api/drowsiness/upload-and-analyze", methods=["POST"])
def upload_and_analyze_drowsiness():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in request."}), 400

    file_storage = request.files["file"]
    if file_storage.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    try:
        filename, abs_path, media_type = save_module_upload(file_storage, "drowsiness")
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    result = drowsiness_service.analyze(abs_path, media_type)

    return jsonify({"success": result.get("status") == "Completed", "result": result})
