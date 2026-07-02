"""
routes/live_detection.py
---------------------------
Live Detection Lab page. Each module card runs fully independently in the
browser via static/js/live_detection.js -- there is intentionally no
unified live pipeline, matching the brief.
"""

from flask import Blueprint, render_template, request, jsonify
import base64
import cv2
import numpy as np
import importlib
from utils import model_loader
from config import Config

live_detection_bp = Blueprint("live_detection", __name__)

LIVE_MODULES = [
    {"key": "lane", "label": "Lane Analysis", "icon": "route"},
    {"key": "traffic_sign", "label": "Traffic Sign Analysis", "icon": "octagon-alert"},
    {"key": "pothole", "label": "Road Surface Inspection", "icon": "construction"},
    {"key": "emergency", "label": "Emergency Vehicle Analysis", "icon": "siren"},
    {"key": "drowsiness", "label": "Driver Monitoring", "icon": "eye"},
]


@live_detection_bp.route("/live-detection")
def live_detection_page():
    return render_template(
        "live_detection.html", active_page="live_detection", modules=LIVE_MODULES
    )


@live_detection_bp.route("/api/live/analyze-frame/<module>", methods=["POST"])
def analyze_frame(module):
    if module not in Config.MODEL_REGISTRY:
        return jsonify({"error": "Invalid module"}), 400
    
    data = request.json
    if not data or "image" not in data:
        return jsonify({"error": "No image provided"}), 400
        
    try:
        header, encoded = data["image"].split(",", 1) if "," in data["image"] else ("", data["image"])
        img_data = base64.b64decode(encoded)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        model_info = model_loader.get_model(module)
        
        if not model_info:
            return jsonify({"error": "Model not loaded"}), 500
            
        handle = model_info["handle"]
        inference_mod = model_info["module"]
        
        if module == "drowsiness":
            annotated, metrics = inference_mod.run_live_frame(handle, frame, model_choice="model.task")
        else:
            annotated, metrics = inference_mod.run_live_frame(handle, frame)
        
        _, buffer = cv2.imencode('.jpg', annotated)
        annotated_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({"success": True, "image": annotated_b64, "metrics": metrics})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
