"""
services/lane_service.py
--------------------------
Service layer for the Lane Detection module. Routes call into this file
only -- never into utils/model_loader or models/lane_detection directly.
"""

from services.base_service import run_module_analysis


def analyze(media_path, media_type):
    """Run lane detection on the given media file and return a result dict."""
    return run_module_analysis("lane", media_path, media_type)
