"""
routes/dashboard.py
---------------------
Home / Command Center dashboard.
"""

from flask import Blueprint, render_template

from services import dashboard_service

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def home():
    summary = dashboard_service.get_dashboard_summary()
    return render_template("dashboard.html", active_page="home", summary=summary)
