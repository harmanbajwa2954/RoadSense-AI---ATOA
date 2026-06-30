"""
routes/crash_alert.py
------------------------
ATOA Crash Detection & Alert System page + REST endpoints.

The page provides:
  - A browser-based crash detection system using device sensors (GPS +
    accelerometer) running entirely client-side
  - Firebase Realtime Database integration for broadcasting alerts to
    nearby drivers
  - Speech synthesis warnings for approaching vehicles
  - Server-side crash logging via the incident_service

Endpoints:
  GET  /crash-alert              — render the ATOA page
  POST /api/crash-alert/log      — log a crash from client sensor data
  GET  /api/crash-alert/active   — list active ATOA alerts
  POST /api/crash-alert/dismiss/<id> — dismiss an alert
"""

from flask import Blueprint, jsonify, render_template, request

from services import crash_alert_service

crash_alert_bp = Blueprint("crash_alert", __name__)


@crash_alert_bp.route("/crash-alert")
def crash_alert_page():
    active_alerts = crash_alert_service.get_active_alerts()
    return render_template(
        "crash_alert.html",
        active_page="crash_alert",
        active_alerts=active_alerts,
    )


@crash_alert_bp.route("/api/crash-alert/log", methods=["POST"])
def api_log_crash():
    """Receive crash telemetry from the browser and create an incident."""
    data = request.get_json(silent=True) or {}

    if not data.get("lat") and not data.get("lon"):
        return jsonify({"success": False, "error": "Missing GPS coordinates."}), 400

    incident = crash_alert_service.log_crash(data)
    return jsonify({"success": True, "incident": incident}), 201


@crash_alert_bp.route("/api/crash-alert/active", methods=["GET"])
def api_active_alerts():
    """Return active ATOA crash alerts."""
    alerts = crash_alert_service.get_active_alerts()
    return jsonify({"success": True, "alerts": alerts})


@crash_alert_bp.route("/api/crash-alert/dismiss/<int:incident_id>", methods=["POST"])
def api_dismiss_alert(incident_id):
    """Mark a crash alert as resolved."""
    result = crash_alert_service.dismiss_alert(incident_id)
    if not result:
        return jsonify({"success": False, "error": "Alert not found."}), 404
    return jsonify({"success": True, "incident": result})
