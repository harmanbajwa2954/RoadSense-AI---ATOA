"""
services/dashboard_service.py
--------------------------------
Aggregates data for the Home dashboard and the Analytics page. Pulls real
counts from analysis_history + incidents where possible, and supplements
with demo-grade mock series for the chart-heavy Analytics view as
explicitly permitted by the brief ("Use mock/demo data initially").
"""

from utils.db import get_connection
from utils import model_loader


def get_dashboard_summary():
    conn = get_connection()
    total_analyses = conn.execute("SELECT COUNT(*) AS c FROM analysis_history").fetchone()["c"]
    active_alerts = conn.execute(
        "SELECT COUNT(*) AS c FROM incidents WHERE status = 'Active'"
    ).fetchone()["c"]
    recent = conn.execute(
        "SELECT * FROM analysis_history ORDER BY id DESC LIMIT 6"
    ).fetchall()
    history = conn.execute(
        "SELECT * FROM analysis_history ORDER BY id DESC LIMIT 12"
    ).fetchall()
    avg_confidence_row = conn.execute(
        "SELECT AVG(confidence) AS avg_c FROM analysis_history WHERE confidence IS NOT NULL"
    ).fetchone()
    conn.close()

    avg_confidence = avg_confidence_row["avg_c"] or 0
    traffic_intelligence_score = round(min(99, 70 + (total_analyses * 1.2)), 1)
    road_safety_score = round(avg_confidence, 1) if avg_confidence else 92.0

    return {
        "traffic_intelligence_score": traffic_intelligence_score,
        "road_safety_score": road_safety_score,
        "total_analyses": total_analyses,
        "active_alerts": active_alerts,
        "recent_activity": [dict(r) for r in recent],
        "analysis_history": [dict(r) for r in history],
        "system_status": model_loader.get_status(),
    }


def get_analytics_data():
    """
    Demo/mock analytics series for Chart.js, as explicitly permitted by the
    brief. Shaped for direct consumption by static/js/analytics.js.
    """
    return {
        "traffic_sign_distribution": {
            "labels": ["Speed Limit", "No Entry", "Pedestrian", "Stop", "Yield", "Warning"],
            "values": [32, 18, 24, 12, 9, 15],
        },
        "lane_detection_stats": {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "stable": [88, 91, 87, 93, 90, 95, 92],
            "drifting": [9, 7, 10, 5, 8, 4, 6],
        },
        "road_hazard_stats": {
            "labels": ["Potholes", "Cracks", "Debris", "Flooding", "Faded Markings"],
            "values": [42, 27, 14, 6, 19],
        },
        "emergency_vehicle_trends": {
            "labels": ["Week 1", "Week 2", "Week 3", "Week 4"],
            "values": [12, 19, 14, 22],
        },
        "crash_trends": {
            "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "values": [8, 11, 7, 14, 9, 6],
        },
        "road_safety_index": {
            "labels": ["Sector 1", "Sector 2", "Sector 3", "Sector 4", "Sector 5"],
            "values": [82, 76, 91, 68, 88],
        },
        "inference_statistics": {
            "labels": ["Lane", "Sign", "Pothole", "Emergency", "Drowsiness"],
            "avg_ms": [410, 190, 520, 370, 630],
        },
    }
