"""
config.py
----------
Central configuration for RoadSense AI.

All paths, upload limits and module metadata live here so that the rest of
the application never hardcodes a path. Routes and services should import
this module rather than re-deriving directory paths themselves.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Core Flask settings -------------------------------------------------
    SECRET_KEY = os.environ.get("ROADSENSE_SECRET_KEY", "roadsense-dev-secret-key")
    DEBUG = True

    # --- Storage ---------------------------------------------------------------
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "roadsense.db")

    UPLOAD_ROOT = os.path.join(BASE_DIR, "uploads")
    OUTPUT_ROOT = os.path.join(BASE_DIR, "outputs")

    UPLOAD_DIRS = {
        "lane": os.path.join(UPLOAD_ROOT, "lane"),
        "traffic_sign": os.path.join(UPLOAD_ROOT, "traffic_sign"),
        "pothole": os.path.join(UPLOAD_ROOT, "pothole"),
        "emergency": os.path.join(UPLOAD_ROOT, "emergency"),
        "drowsiness": os.path.join(UPLOAD_ROOT, "drowsiness"),
    }

    OUTPUT_DIRS = {
        "lane": os.path.join(OUTPUT_ROOT, "lane"),
        "traffic_sign": os.path.join(OUTPUT_ROOT, "traffic_sign"),
        "pothole": os.path.join(OUTPUT_ROOT, "pothole"),
        "emergency": os.path.join(OUTPUT_ROOT, "emergency"),
        "drowsiness": os.path.join(OUTPUT_ROOT, "drowsiness"),
    }

    # Generic workspace upload bucket (Analysis Workspace shares ONE upload
    # across all four tabs, so it gets its own holding directory distinct
    # from the per-module dirs above which store the *processed* copies).
    WORKSPACE_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, "workspace")

    MAX_CONTENT_LENGTH = 250 * 1024 * 1024  # 250 MB ceiling for video uploads

    ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "bmp", "webp"}
    ALLOWED_VIDEO_EXT = {"mp4", "avi", "mov", "mkv", "webm"}

    # --- Model registry ----------------------------------------------------
    # Maps each analysis module to its weight file + inference script.
    # Services use this registry to know where to load from; nothing in
    # routes/ should ever reference models/ paths directly.
    MODEL_REGISTRY = {
        "lane": {
            "name": "Lane Detection",
            "dir": os.path.join(BASE_DIR, "models", "lane_detection"),
            "weights": os.path.join(BASE_DIR, "models", "lane_detection", "model.pth"),
        },
        "traffic_sign": {
            "name": "Traffic Sign Recognition",
            "dir": os.path.join(BASE_DIR, "models", "traffic_sign"),
            "weights": os.path.join(BASE_DIR, "models", "traffic_sign", "model.onnx"),
        },
        "pothole": {
            "name": "Road Surface Inspection",
            "dir": os.path.join(BASE_DIR, "models", "pothole_detection"),
            "weights": os.path.join(BASE_DIR, "models", "pothole_detection", "model.pt"),
        },
        "emergency": {
            "name": "Emergency Vehicle Detection",
            "dir": os.path.join(BASE_DIR, "models", "emergency_vehicle"),
            "weights": os.path.join(BASE_DIR, "models", "emergency_vehicle", "model.pt"),
        },
        "drowsiness": {
            "name": "Driver Drowsiness Detection",
            "dir": os.path.join(BASE_DIR, "models", "driver_drowsiness"),
            "weights": os.path.join(BASE_DIR, "models", "driver_drowsiness", "model.h5"),
        },
    }

    @staticmethod
    def ensure_directories():
        """Create every storage directory the app depends on, if missing."""
        dirs = [
            Config.UPLOAD_ROOT,
            Config.OUTPUT_ROOT,
            Config.WORKSPACE_UPLOAD_DIR,
            os.path.dirname(Config.DATABASE_PATH),
        ]
        dirs.extend(Config.UPLOAD_DIRS.values())
        dirs.extend(Config.OUTPUT_DIRS.values())
        for d in dirs:
            os.makedirs(d, exist_ok=True)
