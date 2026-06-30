"""
routes/settings.py
---------------------
Settings page. Surfaces system/model status (read from the in-memory model
loader) alongside basic platform preferences.
"""

from flask import Blueprint, render_template

from utils import model_loader

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings")
def settings_page():
    status = model_loader.get_status()
    return render_template("settings.html", active_page="settings", model_status=status)
