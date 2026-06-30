"""
services/base_service.py
--------------------------
Shared logic for every analysis service (lane, traffic_sign, pothole,
emergency, drowsiness). Each concrete service module wraps this helper with
its own module_key so routes never reach into utils/model_loader or
models/ directly -- routes only ever call a *_service.py function.
"""

import os
from datetime import datetime

from config import Config
from utils import model_loader
from utils.db import get_connection


def run_module_analysis(module_key, media_path, media_type):
    """
    Run the requested module's inference on a piece of media and log the
    result into analysis_history. Returns a normalized result dict that
    every route/template can render the same way.
    """
    meta = Config.MODEL_REGISTRY[module_key]
    loaded = model_loader.get_model(module_key)

    if loaded is None or loaded.get("module") is None:
        return {
            "status": "Error",
            "module": module_key,
            "module_label": meta["name"],
            "error": "Model not loaded. Check that model.pt and inference.py exist in its models/ directory.",
        }

    inference_module = loaded["module"]
    handle = loaded.get("handle")
    output_dir = Config.OUTPUT_DIRS[module_key]

    try:
        result = inference_module.run_inference(handle, media_path, media_type, output_dir)
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI as a failed run
        _log_history(module_key, meta["name"], os.path.basename(media_path), "Failed", None, None, None)
        return {
            "status": "Failed",
            "module": module_key,
            "module_label": meta["name"],
            "error": str(exc),
        }

    annotated_path = result.get("annotated_path")
    annotated_filename = os.path.basename(annotated_path) if annotated_path else None

    response = {
        "status": "Completed",
        "module": module_key,
        "module_label": meta["name"],
        "model_name": meta["name"],
        "confidence": result.get("confidence"),
        "objects_detected": result.get("objects_detected"),
        "inference_time": result.get("inference_time"),
        "annotated_filename": annotated_filename,
        "media_type": media_type,
        "details": result.get("details", {}),
    }

    _log_history(
        module_key,
        meta["name"],
        os.path.basename(media_path),
        "Completed",
        result.get("confidence"),
        result.get("inference_time"),
        result.get("objects_detected"),
    )

    return response


def _log_history(module_key, module_label, filename, status, confidence, inference_time, objects_detected):
    conn = get_connection()
    conn.execute(
        """INSERT INTO analysis_history
           (module, module_label, source_filename, status, confidence, inference_time, objects_detected, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            module_key,
            module_label,
            filename,
            status,
            confidence,
            inference_time,
            objects_detected,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()
