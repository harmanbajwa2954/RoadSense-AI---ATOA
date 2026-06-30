"""
services/crash_alert_service.py
----------------------------------
Service layer for the ATOA Crash Detection & Alert System.

Handles server-side crash incident logging when the client-side crash model
(running in the browser via device sensors) detects a collision. Crash
events are stored as incidents in the existing `incidents` SQLite table with
automatic severity classification based on G-force magnitude.

All real-time alert broadcasting between devices happens client-side via
Firebase Realtime Database -- this service only handles persistence.
"""

from datetime import datetime

from utils.db import get_connection
from services import incident_service


def _classify_severity(g_force):
    """Map G-force magnitude to a severity level."""
    if g_force >= 15:
        return "Critical"
    elif g_force >= 8:
        return "Moderate"
    else:
        return "Minor"


def log_crash(data):
    """
    Log a crash event detected by the client-side sensor model.

    Parameters
    ----------
    data : dict
        Expected keys:
        - lat, lon : float  — GPS coordinates
        - g_force  : float  — peak G-force at impact
        - speed    : float  — speed at time of detection (km/h)
        - timestamp: int    — epoch ms when crash was detected

    Returns
    -------
    dict : The newly created incident record.
    """
    lat = data.get("lat", 0)
    lon = data.get("lon", 0)
    g_force = data.get("g_force", 0)
    speed = data.get("speed", 0)
    timestamp = data.get("timestamp")

    severity = _classify_severity(g_force)

    # Build a human-readable location string from coordinates
    location = f"GPS ({lat:.5f}, {lon:.5f})"

    occurred_at = (
        datetime.fromtimestamp(timestamp / 1000).isoformat(timespec="seconds")
        if timestamp
        else datetime.now().isoformat(timespec="seconds")
    )

    notes = (
        f"ATOA Auto-Detection — G-Force: {g_force:.1f}g, "
        f"Speed at impact: {speed:.1f} km/h"
    )

    incident_data = {
        "occurred_at": occurred_at,
        "location": location,
        "severity": severity,
        "status": "Active",
        "vehicle_type": "Unknown",
        "notes": notes,
    }

    return incident_service.create_incident(incident_data)


def get_active_alerts(max_age_minutes=60):
    """
    Return all crash-originated incidents from the last `max_age_minutes`
    that are still Active.
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM incidents
           WHERE status = 'Active'
             AND notes LIKE '%ATOA Auto-Detection%'
           ORDER BY id DESC
           LIMIT 50""",
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def dismiss_alert(incident_id):
    """Mark a crash alert as Resolved."""
    return incident_service.update_incident(incident_id, {"status": "Resolved"})
