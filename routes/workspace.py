"""
routes/workspace.py
----------------------
The Analysis Workspace page itself, plus the single shared upload endpoint
that all four tabs (Lane / Traffic Sign / Pothole / Emergency) read from.

Per the brief: there is ONE upload section for the whole workspace. The
per-module analyze endpoints (routes/lane.py, routes/traffic_sign.py,
routes/pothole.py, routes/emergency.py) each take the filename produced
here and run only their own model -- lazy execution, one tab at a time.
"""

import os

from flask import Blueprint, jsonify, render_template, request

from config import Config
from utils.file_utils import save_workspace_upload

workspace_bp = Blueprint("workspace", __name__)


@workspace_bp.route("/workspace")
def workspace_page():
    return render_template("workspace.html", active_page="workspace")


@workspace_bp.route("/api/workspace/upload", methods=["POST"])
def upload_workspace_media():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in request."}), 400

    file_storage = request.files["file"]
    if file_storage.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    try:
        filename, abs_path, media_type = save_workspace_upload(file_storage)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify(
        {
            "success": True,
            "filename": filename,
            "media_type": media_type,
            "preview_url": f"/uploads/workspace/{filename}",
        }
    )


def resolve_workspace_path(filename):
    """Shared helper used by every per-module analyze route."""
    safe_path = os.path.join(Config.WORKSPACE_UPLOAD_DIR, filename)
    if not os.path.isfile(safe_path):
        return None
    return safe_path
