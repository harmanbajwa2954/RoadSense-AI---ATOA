"""
services/pothole_service.py
------------------------------
Service layer for the Road Surface Inspection (pothole) module.
"""

from services.base_service import run_module_analysis


def analyze(media_path, media_type):
    return run_module_analysis("pothole", media_path, media_type)
