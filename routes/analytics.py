"""
routes/analytics.py
----------------------
Analytics dashboard page (Chart.js powered, demo/mock data per the brief).
"""

from flask import Blueprint, jsonify, render_template

from services import dashboard_service

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics")
def analytics_page():
    return render_template("analytics.html", active_page="analytics")


@analytics_bp.route("/api/analytics/data")
def api_analytics_data():
    return jsonify({"success": True, "data": dashboard_service.get_analytics_data()})
