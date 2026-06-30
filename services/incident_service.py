"""
services/incident_service.py
-------------------------------
CRUD service for the Incident Monitoring page. Backed entirely by SQLite
(no permanent file storage is required for incidents per the brief).
"""

from datetime import datetime

from utils.db import get_connection


def list_incidents(severity=None, status=None):
    conn = get_connection()
    query = "SELECT * FROM incidents"
    clauses = []
    params = []

    if severity and severity != "all":
        clauses.append("severity = ?")
        params.append(severity)
    if status and status != "all":
        clauses.append("status = ?")
        params.append(status)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_incident(incident_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_incident(data):
    conn = get_connection()
    cur = conn.cursor()

    next_num = cur.execute("SELECT COUNT(*) AS c FROM incidents").fetchone()["c"] + 1043
    incident_code = f"INC-{next_num}"

    now = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        """INSERT INTO incidents
           (incident_code, occurred_at, location, severity, status, vehicle_type, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            incident_code,
            data.get("occurred_at") or now,
            data.get("location", "Unknown"),
            data.get("severity", "Moderate"),
            data.get("status", "Active"),
            data.get("vehicle_type", "Unknown"),
            data.get("notes", ""),
            now,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return get_incident(new_id)


def update_incident(incident_id, data):
    conn = get_connection()
    existing = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not existing:
        conn.close()
        return None

    merged = dict(existing)
    merged.update({k: v for k, v in data.items() if v is not None})

    conn.execute(
        """UPDATE incidents SET
           location = ?, severity = ?, status = ?, vehicle_type = ?, notes = ?
           WHERE id = ?""",
        (
            merged["location"],
            merged["severity"],
            merged["status"],
            merged["vehicle_type"],
            merged["notes"],
            incident_id,
        ),
    )
    conn.commit()
    conn.close()
    return get_incident(incident_id)


def delete_incident(incident_id):
    conn = get_connection()
    conn.execute("DELETE FROM incidents WHERE id = ?", (incident_id,))
    conn.commit()
    conn.close()
    return True


def get_summary_counts():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) AS c FROM incidents").fetchone()["c"]
    active = conn.execute("SELECT COUNT(*) AS c FROM incidents WHERE status = 'Active'").fetchone()["c"]
    critical = conn.execute("SELECT COUNT(*) AS c FROM incidents WHERE severity = 'Critical'").fetchone()["c"]
    resolved = conn.execute("SELECT COUNT(*) AS c FROM incidents WHERE status = 'Resolved'").fetchone()["c"]
    conn.close()
    return {"total": total, "active": active, "critical": critical, "resolved": resolved}
