"""
routes/media.py
------------------
Serves files out of uploads/ and outputs/ so templates can render previews
and offer "Download Result" buttons without exposing the raw filesystem
layout to the client.
"""

import os

from flask import Blueprint, abort, send_from_directory

from config import Config

media_bp = Blueprint("media", __name__)


@media_bp.route("/uploads/workspace/<path:filename>")
def serve_workspace_upload(filename):
    return send_from_directory(Config.WORKSPACE_UPLOAD_DIR, filename)


@media_bp.route("/uploads/<module_key>/<path:filename>")
def serve_module_upload(module_key, filename):
    directory = Config.UPLOAD_DIRS.get(module_key)
    if not directory:
        abort(404)
    return send_from_directory(directory, filename)


@media_bp.route("/outputs/<module_key>/<path:filename>")
def serve_output(module_key, filename):
    directory = Config.OUTPUT_DIRS.get(module_key)
    if not directory:
        abort(404)
    return send_from_directory(directory, filename)


@media_bp.route("/outputs/<module_key>/<path:filename>/download")
def download_output(module_key, filename):
    directory = Config.OUTPUT_DIRS.get(module_key)
    if not directory or not os.path.isfile(os.path.join(directory, filename)):
        abort(404)
    return send_from_directory(directory, filename, as_attachment=True)
