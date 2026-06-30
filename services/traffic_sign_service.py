"""
services/traffic_sign_service.py
-----------------------------------
Service layer for the Traffic Sign Recognition module.
"""

from services.base_service import run_module_analysis


def analyze(media_path, media_type):
    return run_module_analysis("traffic_sign", media_path, media_type)
