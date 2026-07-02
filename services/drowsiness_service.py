"""
services/drowsiness_service.py
---------------------------------
Service layer for the Driver Drowsiness Detection module. Used exclusively
by the Driver Monitoring page (separate from the Analysis Workspace).
"""

from services.base_service import run_module_analysis


def analyze(media_path, media_type, model_choice="model.h5"):
    return run_module_analysis("drowsiness", media_path, media_type, model_choice=model_choice)
