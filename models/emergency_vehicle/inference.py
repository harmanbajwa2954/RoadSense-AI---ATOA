"""
models/emergency_vehicle/inference.py
----------------------------------------
Emergency Vehicle Detection using a YOLOv8 object detection model.

Classes: ambulance, fire_truck, police
Model format: Ultralytics .pt (loaded via ultralytics.YOLO)
"""

import os
import time

import cv2
from ultralytics import YOLO


# ── Priority mapping by vehicle type ──
_PRIORITY = {
    "ambulance": "Critical",
    "fire_truck": "High",
    "police": "High",
}


def load_model(weights_path):
    """Load the YOLOv8 emergency vehicle detection model."""
    if not os.path.isfile(weights_path):
        return {"weights_path": weights_path, "weights_found": False}

    model = YOLO(weights_path)
    return {
        "weights_path": weights_path,
        "weights_found": True,
        "model": model,
        "class_names": model.names,
    }


def _process_image(model, media_path, output_dir):
    """Run emergency vehicle detection on a single image."""
    results = model.predict(source=media_path, conf=0.35, verbose=False)
    result = results[0]

    annotated = result.plot()
    annotated_filename = f"annotated_{os.path.basename(media_path)}"
    annotated_path = os.path.join(output_dir, annotated_filename)
    cv2.imwrite(annotated_path, annotated)

    detections = []
    for box in result.boxes:
        cls_id = int(box.cls[0])
        name = model.names[cls_id]
        detections.append({
            "class_name": name,
            "confidence": float(box.conf[0]),
            "priority": _PRIORITY.get(name, "Medium"),
        })

    return annotated_path, detections


def _process_video(model, media_path, output_dir):
    """Run emergency vehicle detection on video frames."""
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
        writer.write(result.plot())

        for box in result.boxes:
            cls_id = int(box.cls[0])
            name = model.names[cls_id]
            all_detections.append({
                "class_name": name,
                "confidence": float(box.conf[0]),
                "priority": _PRIORITY.get(name, "Medium"),
            })

    cap.release()
    writer.release()
    return annotated_path, all_detections


def run_inference(handle, media_path, media_type, output_dir):
    """Run emergency vehicle detection on the given media file."""
    start = time.time()
    os.makedirs(output_dir, exist_ok=True)

    model = handle.get("model") if isinstance(handle, dict) else None
    if model is None:
        raise RuntimeError("Emergency vehicle model not loaded.")

    if media_type == "image":
        annotated_path, detections = _process_image(model, media_path, output_dir)
    else:
        annotated_path, detections = _process_video(model, media_path, output_dir)

    elapsed = round(time.time() - start, 3)

    # Determine highest priority detected
    priorities = [d["priority"] for d in detections]
    if "Critical" in priorities:
        top_priority = "Critical"
    elif "High" in priorities:
        top_priority = "High"
    else:
        top_priority = "Low"

    # Get most common vehicle type
    vehicle_types = [d["class_name"] for d in detections]
    from collections import Counter
    most_common = Counter(vehicle_types).most_common(1)
    primary_vehicle = most_common[0][0].replace("_", " ").title() if most_common else "None"

    avg_conf = (sum(d["confidence"] for d in detections) / len(detections) * 100
                if detections else 0)

    return {
        "annotated_path": annotated_path,
        "confidence": round(avg_conf, 1),
        "objects_detected": len(detections),
        "inference_time": elapsed,
        "details": {
            "vehicle_type": primary_vehicle,
            "priority": top_priority,
            "vehicles_found": list({d["class_name"].replace("_", " ").title() for d in detections}),
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
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(annotated, f"{det['class_name']} {det['confidence']:.0%}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    priority = "High (Emergency Vehicle)" if detections else "Normal"
    avg_conf = sum(d["confidence"] for d in detections) / len(detections) * 100 if detections else 0
    metrics = {
        "priority": priority,
        "vehicles_found": str(len(detections)),
        "confidence": f"{round(avg_conf, 1)}%"
    }
    return annotated, metrics
