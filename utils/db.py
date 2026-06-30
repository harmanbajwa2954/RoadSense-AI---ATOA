"""
utils/db.py
-----------
Thin SQLite helper layer.

RoadSense AI uses SQLite for two things:
  1. Incident records (crash / hazard log shown on the Incident Monitoring page)
  2. Analysis history (lightweight log of every module run, used to drive the
     dashboard's "Recent Activity" + "Analysis History" widgets)

No ORM is used on purpose -- the schema is small and the brief calls for a
lightweight, fully-offline footprint.
"""

import sqlite3
from datetime import datetime

from config import Config


def get_connection():
    """Return a new SQLite connection with row access by column name."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they do not already exist. Safe to call on every boot."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_code TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            location TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            vehicle_type TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT NOT NULL,
            module_label TEXT NOT NULL,
            source_filename TEXT,
            status TEXT NOT NULL,
            confidence REAL,
            inference_time REAL,
            objects_detected INTEGER,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()

    # Seed a handful of incidents on first run only, so the Incident
    # Monitoring page never looks empty during a cold demo boot.
    cur.execute("SELECT COUNT(*) AS c FROM incidents")
    if cur.fetchone()["c"] == 0:
        _seed_incidents(conn)

    cur.execute("SELECT COUNT(*) AS c FROM analysis_history")
    if cur.fetchone()["c"] == 0:
        _seed_history(conn)

    conn.close()


def _seed_incidents(conn):
    demo_rows = [
        ("INC-1042", "Sector 4, NH-21 Bypass", "Critical", "Active", "Truck"),
        ("INC-1041", "Sector 2, Ring Road", "Moderate", "Resolved", "Sedan"),
        ("INC-1040", "Sector 7, Industrial Corridor", "Minor", "Resolved", "Motorbike"),
        ("INC-1039", "Sector 9, Flyover Junction", "Critical", "Active", "Bus"),
        ("INC-1038", "Sector 3, Market Road", "Moderate", "Reviewing", "SUV"),
    ]
    now = datetime.now()
    cur = conn.cursor()
    for i, (code, loc, sev, status, vtype) in enumerate(demo_rows):
        cur.execute(
            """INSERT INTO incidents
               (incident_code, occurred_at, location, severity, status, vehicle_type, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                code,
                now.isoformat(timespec="seconds"),
                loc,
                sev,
                status,
                vtype,
                "Auto-logged from detection pipeline.",
                now.isoformat(timespec="seconds"),
            ),
        )
    conn.commit()


def _seed_history(conn):
    demo_rows = [
        ("lane", "Lane Detection", "highway_clip_03.mp4", "Completed", 94.2, 0.41, 3),
        ("traffic_sign", "Traffic Sign Recognition", "intersection_07.jpg", "Completed", 88.7, 0.19, 2),
        ("pothole", "Road Surface Inspection", "city_road_12.mp4", "Completed", 91.5, 0.52, 5),
        ("emergency", "Emergency Vehicle Detection", "siren_test_02.mp4", "Completed", 96.1, 0.37, 1),
        ("drowsiness", "Driver Drowsiness Detection", "driver_session_09.mp4", "Completed", 89.9, 0.63, 1),
    ]
    now = datetime.now()
    cur = conn.cursor()
    for module, label, fname, status, conf, t, n in demo_rows:
        cur.execute(
            """INSERT INTO analysis_history
               (module, module_label, source_filename, status, confidence, inference_time, objects_detected, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (module, label, fname, status, conf, t, n, now.isoformat(timespec="seconds")),
        )
    conn.commit()
