"""
services/emergency_service.py
--------------------------------
Service layer for the Emergency Vehicle Detection module.
"""

from services.base_service import run_module_analysis


def analyze(media_path, media_type):
    return run_module_analysis("emergency", media_path, media_type)
