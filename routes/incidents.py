"""
routes/incidents.py
----------------------
Incident Monitoring page + CRUD APIs backed by SQLite.
"""

from flask import Blueprint, jsonify, render_template, request

from services import incident_service

incidents_bp = Blueprint("incidents", __name__)


@incidents_bp.route("/incidents")
def incidents_page():
    incidents = incident_service.list_incidents()
    summary = incident_service.get_summary_counts()
    return render_template(
        "incidents.html", active_page="incidents", incidents=incidents, summary=summary
    )


@incidents_bp.route("/api/incidents", methods=["GET"])
def api_list_incidents():
    severity = request.args.get("severity")
    status = request.args.get("status")
    incidents = incident_service.list_incidents(severity=severity, status=status)
    return jsonify({"success": True, "incidents": incidents})


@incidents_bp.route("/api/incidents", methods=["POST"])
def api_create_incident():
    data = request.get_json(silent=True) or {}
    incident = incident_service.create_incident(data)
    return jsonify({"success": True, "incident": incident}), 201


@incidents_bp.route("/api/incidents/<int:incident_id>", methods=["GET"])
def api_get_incident(incident_id):
    incident = incident_service.get_incident(incident_id)
    if not incident:
        return jsonify({"success": False, "error": "Incident not found."}), 404
    return jsonify({"success": True, "incident": incident})


@incidents_bp.route("/api/incidents/<int:incident_id>", methods=["PUT"])
def api_update_incident(incident_id):
    data = request.get_json(silent=True) or {}
    incident = incident_service.update_incident(incident_id, data)
    if not incident:
        return jsonify({"success": False, "error": "Incident not found."}), 404
    return jsonify({"success": True, "incident": incident})


@incidents_bp.route("/api/incidents/<int:incident_id>", methods=["DELETE"])
def api_delete_incident(incident_id):
    incident = incident_service.get_incident(incident_id)
    if not incident:
        return jsonify({"success": False, "error": "Incident not found."}), 404
    incident_service.delete_incident(incident_id)
    return jsonify({"success": True})
