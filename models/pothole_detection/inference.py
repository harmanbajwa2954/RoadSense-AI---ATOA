"""
models/pothole_detection/inference.py
----------------------------------------
Road Surface Inspection using a YOLOv8 object detection model.

Classes: Longitudinal_Crack, Transverse_Crack, Alligator_Crack, Pothole
Model format: Ultralytics .pt (loaded via ultralytics.YOLO)
"""

import os
import time

import cv2
from ultralytics import YOLO


# ── Severity mapping based on detection count + class mix ──
_SEVERITY_MAP = {
    "Pothole": 3,  # highest severity weight
    "Alligator_Crack": 2,
    "Transverse_Crack": 1,
    "Longitudinal_Crack": 1,
}


def load_model(weights_path):
    """Load the YOLOv8 pothole/crack detection model."""
    if not os.path.isfile(weights_path):
        return {"weights_path": weights_path, "weights_found": False}

    model = YOLO(weights_path)
    return {
        "weights_path": weights_path,
        "weights_found": True,
        "model": model,
        "class_names": model.names,
    }


def _assess_severity(detections):
    """Compute an overall severity rating from detections."""
    if not detections:
        return "None"
    total_weight = sum(_SEVERITY_MAP.get(d["class_name"], 1) for d in detections)
    if total_weight >= 8 or any(d["class_name"] == "Pothole" for d in detections):
        return "Critical"
    elif total_weight >= 4:
        return "Moderate"
    else:
        return "Minor"


def _process_image(model, media_path, output_dir):
    """Run pothole/crack detection on a single image."""
    results = model.predict(source=media_path, conf=0.35, verbose=False)
    result = results[0]

    annotated = result.plot()
    annotated_filename = f"annotated_{os.path.basename(media_path)}"
    annotated_path = os.path.join(output_dir, annotated_filename)
    cv2.imwrite(annotated_path, annotated)

    detections = []
    for box in result.boxes:
        cls_id = int(box.cls[0])
        detections.append({
            "class_name": model.names[cls_id],
            "confidence": float(box.conf[0]),
            "box": box.xyxy[0].tolist(),
        })

    return annotated_path, detections


def _process_video(model, media_path, output_dir):
    """Run pothole/crack detection on video frames."""
    cap = cv2.VideoCapture(media_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot read video: {media_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    annotated_filename = f"annotated_{os.path.basename(media_path)}"
    annotated_path = os.path.join(output_dir, annotated_filename)
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    writer = cv2.VideoWriter(annotated_path, fourcc, fps, (w, h))

    all_detections = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model.predict(source=frame, conf=0.35, verbose=False)
        result = results[0]
        annotated_frame = result.plot()
        writer.write(annotated_frame)

        for box in result.boxes:
            cls_id = int(box.cls[0])
            all_detections.append({
                "class_name": model.names[cls_id],
                "confidence": float(box.conf[0]),
            })

    cap.release()
    writer.release()
    return annotated_path, all_detections


def run_inference(handle, media_path, media_type, output_dir):
    """Run road surface inspection on the given media file."""
    start = time.time()
    os.makedirs(output_dir, exist_ok=True)

    model = handle.get("model") if isinstance(handle, dict) else None
    if model is None:
        raise RuntimeError("Pothole detection model not loaded.")

    if media_type == "image":
        annotated_path, detections = _process_image(model, media_path, output_dir)
    else:
        annotated_path, detections = _process_video(model, media_path, output_dir)

    elapsed = round(time.time() - start, 3)

    severity = _assess_severity(detections)
    avg_conf = (sum(d["confidence"] for d in detections) / len(detections) * 100
                if detections else 0)

    # Count by damage type
    damage_counts = {}
    for d in detections:
        name = d["class_name"]
        damage_counts[name] = damage_counts.get(name, 0) + 1

    return {
        "annotated_path": annotated_path,
        "confidence": round(avg_conf, 1),
        "objects_detected": len(detections),
        "inference_time": elapsed,
        "details": {
            "severity": severity,
            "surface_damage_count": len(detections),
            "damage_types": damage_counts,
        },
    }

def run_live_frame(handle, frame):
    model = handle.get("model") if isinstance(handle, dict) else None
    if model is None: return frame, {}
    results = model.predict(source=frame, verbose=False)
    detections = []
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())
            name = model.names[cls_id]
            detections.append({"box": [x1, y1, x2, y2], "confidence": conf, "class_name": name})
    annotated = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        import cv2
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(annotated, f"{det['class_name']} {det['confidence']:.0%}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    severity = "High" if len(detections) > 3 else "Medium" if len(detections) > 0 else "Low"
    avg_conf = sum(d["confidence"] for d in detections) / len(detections) * 100 if detections else 0
    metrics = {
        "severity": severity,
        "surface_damage_count": str(len(detections)),
        "confidence": f"{round(avg_conf, 1)}%"
    }
    return annotated, metrics
