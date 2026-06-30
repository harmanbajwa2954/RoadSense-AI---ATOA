"""
models/lane_detection/inference.py
------------------------------------
Lane Detection module using a lightweight U-Net segmentation model.

The model takes 3-channel RGB images and outputs a single-channel lane
segmentation mask. This inference script:
  1. Loads the model from a PyTorch .pth state_dict
  2. For images: runs a single forward pass and overlays the lane mask
  3. For videos: processes each frame and writes annotated output

Architecture (from the checkpoint):
  Encoder: enc1(3→16) + enc2(16→32) with MaxPool
  Bottleneck: 32→64
  Decoder: up1+dec1(64→32) + up2+dec2(32→16) with skip connections
  Final: 1x1 conv → sigmoid (binary lane mask)
"""

import os
import time

import cv2
import numpy as np
import torch
import torch.nn as nn


class LaneUNet(nn.Module):
    """Compact U-Net matching the .pth checkpoint structure."""

    def __init__(self):
        super().__init__()
        self.enc1 = nn.Sequential(nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(),
                                  nn.Conv2d(16, 16, 3, padding=1), nn.ReLU())
        self.enc2 = nn.Sequential(nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(),
                                  nn.Conv2d(32, 32, 3, padding=1), nn.ReLU())
        self.pool = nn.MaxPool2d(2)

        self.bottleneck = nn.Sequential(nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(),
                                        nn.Conv2d(64, 64, 3, padding=1), nn.ReLU())

        self.up1 = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.dec1 = nn.Sequential(nn.Conv2d(64, 32, 3, padding=1), nn.ReLU(),
                                  nn.Conv2d(32, 32, 3, padding=1), nn.ReLU())

        self.up2 = nn.ConvTranspose2d(32, 16, 2, stride=2)
        self.dec2 = nn.Sequential(nn.Conv2d(32, 16, 3, padding=1), nn.ReLU(),
                                  nn.Conv2d(16, 16, 3, padding=1), nn.ReLU())

        self.final = nn.Sequential(nn.Conv2d(16, 1, 1))

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        b = self.bottleneck(self.pool(e2))
        d1 = self.dec1(torch.cat([self.up1(b), e2], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d1), e1], dim=1))
        return torch.sigmoid(self.final(d2))


# ── Model input size (must be divisible by 4 for two pooling layers) ──
INPUT_H, INPUT_W = 256, 256


def load_model(weights_path):
    """Load the lane U-Net from a .pth state_dict file."""
    if not os.path.isfile(weights_path):
        return {"weights_path": weights_path, "weights_found": False}

    model = LaneUNet()
    state = torch.load(weights_path, map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    return {"weights_path": weights_path, "weights_found": True, "model": model}


def _preprocess(frame):
    """Resize + normalise a BGR frame to a [1,3,H,W] tensor."""
    img = cv2.resize(frame, (INPUT_W, INPUT_H))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    tensor = torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0)
    return tensor


def _overlay_mask(frame, mask, color=(0, 255, 100), alpha=0.45):
    """
    Overlay a binary lane mask on the original frame.
    `mask` is a [H,W] float array in [0,1]; thresholded at 0.5.
    """
    h, w = frame.shape[:2]
    mask_resized = cv2.resize(mask, (w, h))
    binary = (mask_resized > 0.5).astype(np.uint8)

    overlay = frame.copy()
    overlay[binary == 1] = color
    blended = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)

    # Draw lane contours for visual clarity
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(blended, contours, -1, color, 2)

    return blended, int(np.sum(binary > 0))


def _detect_lanes_status(mask):
    """Estimate lane status from the segmentation mask."""
    binary = (mask > 0.5).astype(np.uint8)
    total_pixels = binary.size
    lane_pixels = int(np.sum(binary))
    coverage = lane_pixels / max(total_pixels, 1)

    # Count distinct lane regions
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    significant = [c for c in contours if cv2.contourArea(c) > 50]
    lane_count = len(significant)

    if lane_count >= 2 and coverage > 0.02:
        status = "Stable"
    elif lane_count >= 1 and coverage > 0.01:
        status = "Drifting"
    else:
        status = "Lost"

    return status, lane_count, round(coverage * 100, 1)


def _process_image(model, media_path, output_dir):
    """Run lane detection on a single image."""
    frame = cv2.imread(media_path)
    if frame is None:
        raise ValueError(f"Cannot read image: {media_path}")

    tensor = _preprocess(frame)
    with torch.no_grad():
        pred = model(tensor)
    mask = pred.squeeze().numpy()

    annotated, lane_px = _overlay_mask(frame, mask)
    status, lane_count, coverage = _detect_lanes_status(mask)

    annotated_filename = f"annotated_{os.path.basename(media_path)}"
    annotated_path = os.path.join(output_dir, annotated_filename)
    cv2.imwrite(annotated_path, annotated)

    confidence = min(99.9, 70 + coverage * 3) if lane_count > 0 else 25.0

    return annotated_path, confidence, lane_count, status


def _process_video(model, media_path, output_dir):
    """Run lane detection on each video frame."""
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

    total_lanes = 0
    frame_count = 0
    all_statuses = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        tensor = _preprocess(frame)
        with torch.no_grad():
            pred = model(tensor)
        mask = pred.squeeze().numpy()

        annotated_frame, _ = _overlay_mask(frame, mask)
        status, lane_count, _ = _detect_lanes_status(mask)

        writer.write(annotated_frame)
        total_lanes = max(total_lanes, lane_count)
        all_statuses.append(status)
        frame_count += 1

    cap.release()
    writer.release()

    # Determine overall status from frame statuses
    if all_statuses:
        from collections import Counter
        most_common = Counter(all_statuses).most_common(1)[0][0]
    else:
        most_common = "Lost"

    return annotated_path, total_lanes, most_common, frame_count


def run_inference(handle, media_path, media_type, output_dir):
    """Run lane detection on the given media file."""
    start = time.time()
    os.makedirs(output_dir, exist_ok=True)

    model = handle.get("model") if isinstance(handle, dict) else None
    if model is None:
        raise RuntimeError("Lane detection model not loaded.")

    if media_type == "image":
        annotated_path, confidence, lane_count, status = _process_image(
            model, media_path, output_dir
        )
        elapsed = round(time.time() - start, 3)
        return {
            "annotated_path": annotated_path,
            "confidence": round(confidence, 1),
            "objects_detected": lane_count,
            "inference_time": elapsed,
            "details": {
                "lane_status": status,
                "lane_count": lane_count,
            },
        }
    else:
        annotated_path, lane_count, status, frame_count = _process_video(
            model, media_path, output_dir
        )
        elapsed = round(time.time() - start, 3)
        return {
            "annotated_path": annotated_path,
            "confidence": 90.0 if status == "Stable" else 70.0,
            "objects_detected": lane_count,
            "inference_time": elapsed,
            "details": {
                "lane_status": status,
                "lane_count": lane_count,
                "frames_processed": frame_count,
            },
        }

def run_live_frame(handle, frame):
    model = handle.get("model") if isinstance(handle, dict) else None
    if model is None: return frame, {}
    tensor = _preprocess(frame)
    import torch
    with torch.no_grad():
        pred = model(tensor)
    mask = pred.squeeze().numpy()
    annotated, lane_px = _overlay_mask(frame.copy(), mask)
    status, lane_count, coverage = _detect_lanes_status(mask)
    confidence = min(99.9, 70 + coverage * 3) if lane_count > 0 else 25.0
    metrics = {
        "lane_status": status,
        "lane_count": str(lane_count),
        "confidence": f"{round(confidence, 1)}%"
    }
    return annotated, metrics
