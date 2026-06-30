"""
models/traffic_sign/inference.py
-----------------------------------
Traffic Sign Recognition using an ONNX-exported YOLOv8 detection model.

The model was exported from Ultralytics YOLOv8 and expects:
  Input:  [1, 3, 640, 640] float32 (RGB, 0-1 normalised)
  Output: [1, 61, 8400]  (4 bbox coords + 57 class scores × 8400 anchors)

57 traffic sign classes from Indian road signs dataset.
"""

import ast
import os
import time

import cv2
import numpy as np
import onnxruntime as ort


# ── ONNX NMS + post-processing constants ──
CONF_THRESHOLD = 0.35
NMS_IOU_THRESHOLD = 0.45
INPUT_SIZE = 640

# Colors for bounding box drawing (cycling palette)
_COLORS = [
    (0, 255, 127), (255, 200, 50), (50, 180, 255), (255, 80, 80),
    (180, 120, 255), (100, 255, 200), (255, 160, 100), (80, 200, 255),
]


def load_model(weights_path):
    """Load the ONNX YOLOv8 traffic sign model."""
    if not os.path.isfile(weights_path):
        return {"weights_path": weights_path, "weights_found": False}

    session = ort.InferenceSession(weights_path, providers=["CPUExecutionProvider"])
    meta = session.get_modelmeta().custom_metadata_map
    names = ast.literal_eval(meta.get("names", "{}"))

    return {
        "weights_path": weights_path,
        "weights_found": True,
        "session": session,
        "class_names": names,
        "input_name": session.get_inputs()[0].name,
    }


def _preprocess(frame):
    """Resize + normalise a BGR frame to [1,3,640,640] float32."""
    img = cv2.resize(frame, (INPUT_SIZE, INPUT_SIZE))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return img.transpose(2, 0, 1)[np.newaxis, ...]  # [1,3,H,W]


def _postprocess(output, orig_h, orig_w, class_names):
    """
    YOLOv8 ONNX output is [1, 61, 8400].
    Transpose to [8400, 61] → first 4 are cx,cy,w,h, rest are class scores.
    Apply confidence threshold and NMS.
    """
    preds = output[0].squeeze().T  # [8400, 61]
    boxes_xywh = preds[:, :4]
    scores_all = preds[:, 4:]

    max_scores = np.max(scores_all, axis=1)
    class_ids = np.argmax(scores_all, axis=1)

    mask = max_scores > CONF_THRESHOLD
    boxes_xywh = boxes_xywh[mask]
    max_scores = max_scores[mask]
    class_ids = class_ids[mask]

    if len(boxes_xywh) == 0:
        return []

    # Convert cxcywh → x1y1x2y2 and scale to original image
    scale_x = orig_w / INPUT_SIZE
    scale_y = orig_h / INPUT_SIZE

    x1 = (boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2) * scale_x
    y1 = (boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2) * scale_y
    x2 = (boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2) * scale_x
    y2 = (boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2) * scale_y

    boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1).astype(int)

    # NMS
    indices = cv2.dnn.NMSBoxes(
        boxes_xyxy.tolist(), max_scores.tolist(),
        CONF_THRESHOLD, NMS_IOU_THRESHOLD,
    )
    if len(indices) == 0:
        return []

    results = []
    for i in indices:
        idx = i[0] if isinstance(i, (list, np.ndarray)) else i
        cls_id = int(class_ids[idx])
        name = class_names.get(cls_id, f"class_{cls_id}")
        # Clean up class name for display
        display_name = name.replace("_", " ").title()
        results.append({
            "box": boxes_xyxy[idx].tolist(),
            "class_id": cls_id,
            "class_name": display_name,
            "confidence": float(max_scores[idx]),
        })

    return results


def _draw_detections(frame, detections):
    """Draw bounding boxes and labels on the frame."""
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        color = _COLORS[det["class_id"] % len(_COLORS)]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        label = f"{det['class_name']} {det['confidence']:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    return frame


def _process_image(handle, media_path, output_dir):
    """Run traffic sign detection on a single image."""
    session = handle["session"]
    class_names = handle["class_names"]
    input_name = handle["input_name"]

    frame = cv2.imread(media_path)
    if frame is None:
        raise ValueError(f"Cannot read image: {media_path}")

    h, w = frame.shape[:2]
    blob = _preprocess(frame)
    outputs = session.run(None, {input_name: blob})
    detections = _postprocess(outputs, h, w, class_names)

    annotated = _draw_detections(frame.copy(), detections)
    annotated_filename = f"annotated_{os.path.basename(media_path)}"
    annotated_path = os.path.join(output_dir, annotated_filename)
    cv2.imwrite(annotated_path, annotated)

    return annotated_path, detections


def _process_video(handle, media_path, output_dir):
    """Run traffic sign detection on each video frame."""
    session = handle["session"]
    class_names = handle["class_names"]
    input_name = handle["input_name"]

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

        blob = _preprocess(frame)
        outputs = session.run(None, {input_name: blob})
        detections = _postprocess(outputs, h, w, class_names)
        all_detections.extend(detections)

        annotated = _draw_detections(frame.copy(), detections)
        writer.write(annotated)

    cap.release()
    writer.release()
    return annotated_path, all_detections


def run_inference(handle, media_path, media_type, output_dir):
    """Run traffic sign recognition on the given media file."""
    start = time.time()
    os.makedirs(output_dir, exist_ok=True)

    if not isinstance(handle, dict) or handle.get("session") is None:
        raise RuntimeError("Traffic sign model not loaded.")

    if media_type == "image":
        annotated_path, detections = _process_image(handle, media_path, output_dir)
    else:
        annotated_path, detections = _process_video(handle, media_path, output_dir)

    elapsed = round(time.time() - start, 3)

    # Collect unique sign names found
    unique_signs = list({d["class_name"] for d in detections})
    avg_conf = (sum(d["confidence"] for d in detections) / len(detections) * 100
                if detections else 0)

    return {
        "annotated_path": annotated_path,
        "confidence": round(avg_conf, 1),
        "objects_detected": len(detections),
        "inference_time": elapsed,
        "details": {
            "signs_found": unique_signs[:10],  # Top 10 unique signs
        },
    }

def run_live_frame(handle, frame):
    session = handle["session"]
    class_names = handle["class_names"]
    input_name = handle["input_name"]
    h, w = frame.shape[:2]
    blob = _preprocess(frame)
    outputs = session.run(None, {input_name: blob})
    detections = _postprocess(outputs, h, w, class_names)
    annotated = _draw_detections(frame.copy(), detections)
    unique_signs = list({d["class_name"] for d in detections})
    avg_conf = sum(d["confidence"] for d in detections) / len(detections) * 100 if detections else 0
    metrics = {
        "signs_found": ", ".join(unique_signs[:3]) if unique_signs else "None",
        "objects_detected": str(len(detections)),
        "confidence": f"{round(avg_conf, 1)}%"
    }
    return annotated, metrics
