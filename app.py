"""
app.py
-------
RoadSense AI -- main Flask application entrypoint.

Responsibilities of this file ONLY:
  - create the Flask app
  - apply config
  - ensure storage directories + SQLite schema exist
  - load every AI model ONCE into memory
  - register every blueprint

No business logic, no model calls, and no database queries belong here.
Those all live in services/ and routes/ respectively, per the
Routes -> Services -> Model Inference architecture described in the brief.
"""

from flask import Flask

from config import Config
from utils.db import init_db
from utils import model_loader

# Blueprints
from routes.dashboard import dashboard_bp
from routes.workspace import workspace_bp
from routes.lane import lane_bp
from routes.traffic_sign import traffic_sign_bp
from routes.pothole import pothole_bp
from routes.emergency import emergency_bp
from routes.drowsiness import drowsiness_bp
from routes.incidents import incidents_bp
from routes.live_detection import live_detection_bp
from routes.analytics import analytics_bp
from routes.settings import settings_bp
from routes.media import media_bp
from routes.crash_alert import crash_alert_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Storage & schema -------------------------------------------------
    Config.ensure_directories()
    init_db()

    # --- AI models: load exactly once, kept in memory for app lifetime ---
    print("\n[RoadSense AI] Loading models into memory ...")
    status = model_loader.load_all_models()
    for key, info in status.items():
        flag = "OK" if info["loaded"] else "MISSING"
        print(f"  - {info['name']:<32} [{flag}]  ({info['load_time']}s)")
    print("[RoadSense AI] Model warm-up complete.\n")

    # --- Blueprints ---------------------------------------------------------
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(workspace_bp)
    app.register_blueprint(lane_bp)
    app.register_blueprint(traffic_sign_bp)
    app.register_blueprint(pothole_bp)
    app.register_blueprint(emergency_bp)
    app.register_blueprint(drowsiness_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(live_detection_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(crash_alert_bp)

    return app


app = create_app()

if __name__ == "__main__":
    # Offline, local-only viva demonstration server.
    app.run(host="127.0.0.1", port=5000, debug=True)
