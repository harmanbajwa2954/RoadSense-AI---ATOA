"""
models/driver_drowsiness/inference.py
----------------------------------------
Driver Drowsiness Detection using a MobileNetV2 binary classifier.

The model is a classifier with a 4-class output head:
0 = alert, 1 = sleepy, 2 = slowBlink, 3 = yawning.

Input: 224×224 RGB normalised image (0-1 range)
Output: 4-class softmax probability
"""

import os
import time

import cv2
import numpy as np


# ── Labels (mapped from the 4-class head) ──
CLASS_NAMES = ["alert", "sleepy", "slowBlink", "yawning"]

# ── Input size ──
INPUT_SIZE = 224


def load_model(weights_path):
    """Load the models for driver drowsiness detection."""
    model_dir = os.path.dirname(weights_path)
    h5_path = os.path.join(model_dir, "model.h5")
    pth_path = os.path.join(model_dir, "model.pth")
    task_path = os.path.join(model_dir, "model.task")

    model = None
    if os.path.isfile(h5_path):
        import tensorflow as tf
        model = tf.keras.models.load_model(h5_path)

    mp_classifier = None
    if os.path.isfile(task_path):
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            base_options = python.BaseOptions(model_asset_path=task_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=False,
                num_faces=1)
            mp_classifier = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            print(f"Warning: Failed to load MediaPipe model: {e}")

    return {
        "weights_path": weights_path,
        "weights_found": model is not None or mp_classifier is not None,
        "model": model,
        "mp_classifier": mp_classifier,
        "pth_path": pth_path if os.path.isfile(pth_path) else None,
        "task_path": task_path if os.path.isfile(task_path) else None,
    }


def _preprocess(frame):
    """Resize + normalise a BGR frame to [1, 224, 224, 3] tensor."""
    img = cv2.resize(frame, (INPUT_SIZE, INPUT_SIZE))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    tensor = np.expand_dims(img, axis=0)
    return tensor


def _classify_frame(model, frame):
    """Run classification on a single frame, return prediction dict."""
    tensor = _preprocess(frame)
    probs = model.predict(tensor, verbose=0)[0]

    class_index = int(np.argmax(probs))
    predicted_class = CLASS_NAMES[class_index]
    confidence = float(np.max(probs))

    # Calculate overall drowsy probability as the sum of non-alert probabilities
    # 0: alert, 1: sleepy, 2: slowBlink, 3: yawning
    drowsy_prob = float(probs[1] + probs[2] + probs[3])

    if predicted_class == "sleepy":
        driver_status = "Drowsy"
        eye_status = "Closed"
        yawning_status = "Not Detected"
        fatigue_level = "Critical"
    elif predicted_class == "slowBlink":
        driver_status = "Fatigued"
        eye_status = "Half-Closed"
        yawning_status = "Not Detected"
        fatigue_level = "High"
    elif predicted_class == "yawning":
        driver_status = "Fatigued"
        eye_status = "Open"
        yawning_status = "Detected"
        fatigue_level = "Moderate"
    else:
        driver_status = "Alert"
        eye_status = "Open"
        yawning_status = "Not Detected"
        fatigue_level = "Low"

    return {
        "driver_status": driver_status,
        "eye_status": eye_status,
        "yawning_status": yawning_status,
        "fatigue_level": fatigue_level,
        "drowsy_probability": round(drowsy_prob * 100, 1),
        "confidence": round(confidence * 100, 1),
        "class_name": predicted_class
    }

def _classify_frame_mp(mp_classifier, frame):
    """Run classification on a single frame using MediaPipe FaceLandmarker."""
    import mediapipe as mp
    
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    
    result = mp_classifier.detect(mp_image)
    
    predicted_class = "alert"
    confidence = 1.0
    drowsy_prob = 0.0
    
    if result.face_blendshapes and len(result.face_blendshapes) > 0:
        blendshapes = result.face_blendshapes[0]
        
        eye_blink_left = 0.0
        eye_blink_right = 0.0
        jaw_open = 0.0
        
        for category in blendshapes:
            if category.category_name == "eyeBlinkLeft":
                eye_blink_left = category.score
            elif category.category_name == "eyeBlinkRight":
                eye_blink_right = category.score
            elif category.category_name == "jawOpen":
                jaw_open = category.score
                
        blink_score = (eye_blink_left + eye_blink_right) / 2.0
        yawn_score = jaw_open
        
        if yawn_score > 0.5:
            predicted_class = "yawning"
            confidence = yawn_score
            drowsy_prob = yawn_score
        elif blink_score > 0.6:
            predicted_class = "sleepy"
            confidence = blink_score
            drowsy_prob = blink_score
        elif blink_score > 0.4:
            predicted_class = "slowBlink"
            confidence = blink_score
            drowsy_prob = blink_score
        else:
            predicted_class = "alert"
            confidence = 1.0 - max(blink_score, yawn_score)
            drowsy_prob = max(blink_score, yawn_score)

    if predicted_class == "sleepy":
        driver_status = "Drowsy"
        eye_status = "Closed"
        yawning_status = "Not Detected"
        fatigue_level = "Critical"
    elif predicted_class == "slowBlink":
        driver_status = "Fatigued"
        eye_status = "Half-Closed"
        yawning_status = "Not Detected"
        fatigue_level = "High"
    elif predicted_class == "yawning":
        driver_status = "Fatigued"
        eye_status = "Open"
        yawning_status = "Detected"
        fatigue_level = "Moderate"
    else:
        predicted_class = "alert"
        driver_status = "Alert"
        eye_status = "Open"
        yawning_status = "Not Detected"
        fatigue_level = "Low"

    return {
        "driver_status": driver_status,
        "eye_status": eye_status,
        "yawning_status": yawning_status,
        "fatigue_level": fatigue_level,
        "drowsy_probability": round(drowsy_prob * 100, 1),
        "confidence": round(confidence * 100, 1),
        "class_name": predicted_class
    }



def _draw_status(frame, prediction):
    """Draw status overlay on the frame."""
    status = prediction["driver_status"]
    color = (0, 0, 255) if status == "Drowsy" else (0, 200, 255) if status == "Fatigued" else (0, 255, 0)

    # Status banner at top
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (0, 0, 0), -1)
    label = f"Driver: {status} | Eyes: {prediction['eye_status']} | Fatigue: {prediction['fatigue_level']}"
    cv2.putText(frame, label, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Drowsy probability bar
    bar_w = int(frame.shape[1] * 0.3)
    bar_h = 12
    x0, y0 = frame.shape[1] - bar_w - 10, 50
    fill = int(bar_w * prediction["drowsy_probability"] / 100)
    cv2.rectangle(frame, (x0, y0), (x0 + bar_w, y0 + bar_h), (40, 40, 40), -1)
    cv2.rectangle(frame, (x0, y0), (x0 + fill, y0 + bar_h), color, -1)
    cv2.putText(frame, f"Drowsy: {prediction['drowsy_probability']}%",
                (x0, y0 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

    return frame


def _process_image(model, mp_classifier, model_choice, media_path, output_dir):
    """Run drowsiness classification on a single image."""
    frame = cv2.imread(media_path)
    if frame is None:
        raise ValueError(f"Cannot read image: {media_path}")

    if model_choice == "model.task":
        prediction = _classify_frame_mp(mp_classifier, frame)
    else:
        prediction = _classify_frame(model, frame)
        
    annotated = _draw_status(frame.copy(), prediction)

    annotated_filename = f"annotated_{os.path.basename(media_path)}"
    annotated_path = os.path.join(output_dir, annotated_filename)
    cv2.imwrite(annotated_path, annotated)

    return annotated_path, prediction


def _process_video(model, mp_classifier, model_choice, media_path, output_dir):
    """Run drowsiness classification on video frames."""
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

    drowsy_frames = 0
    total_frames = 0
    last_prediction = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if model_choice == "model.task":
            prediction = _classify_frame_mp(mp_classifier, frame)
        else:
            prediction = _classify_frame(model, frame)
            
        last_prediction = prediction

        if prediction["driver_status"] in ("Drowsy", "Fatigued"):
            drowsy_frames += 1
        total_frames += 1

        annotated = _draw_status(frame.copy(), prediction)
        writer.write(annotated)

    cap.release()
    writer.release()

    # Compute overall fatigue assessment
    if total_frames > 0:
        drowsy_ratio = drowsy_frames / total_frames
        if drowsy_ratio > 0.5:
            overall_fatigue = "Critical"
        elif drowsy_ratio > 0.3:
            overall_fatigue = "High"
        elif drowsy_ratio > 0.1:
            overall_fatigue = "Moderate"
        else:
            overall_fatigue = "Low"
    else:
        overall_fatigue = "Unknown"

    if last_prediction:
        last_prediction["fatigue_level"] = overall_fatigue

    return annotated_path, last_prediction or {}, total_frames


def run_inference(handle, media_path, media_type, output_dir, model_choice="model.h5"):
    """Run drowsiness detection on the given media file."""
    if model_choice == "model.pth":
        raise NotImplementedError("PyTorch inference is not implemented yet. Please provide the model architecture class.")
        
    start = time.time()
    os.makedirs(output_dir, exist_ok=True)

    model = handle.get("model") if isinstance(handle, dict) else None
    mp_classifier = handle.get("mp_classifier") if isinstance(handle, dict) else None
    
    if model_choice == "model.h5" and model is None:
        raise RuntimeError("TensorFlow drowsiness model not loaded.")
    if model_choice == "model.task" and mp_classifier is None:
        raise RuntimeError("MediaPipe drowsiness model not loaded.")

    if media_type == "image":
        annotated_path, prediction = _process_image(model, mp_classifier, model_choice, media_path, output_dir)
        elapsed = round(time.time() - start, 3)
        return {
            "annotated_path": annotated_path,
            "confidence": prediction["confidence"],
            "objects_detected": 1,
            "inference_time": elapsed,
            "details": {
                "driver_status": prediction["driver_status"],
                "eye_status": prediction["eye_status"],
                "yawning_status": prediction["yawning_status"],
                "fatigue_level": prediction["fatigue_level"],
            },
        }
    else:
        annotated_path, prediction, frame_count = _process_video(
            model, mp_classifier, model_choice, media_path, output_dir
        )
        elapsed = round(time.time() - start, 3)
        return {
            "annotated_path": annotated_path,
            "confidence": prediction.get("confidence", 0),
            "objects_detected": 1,
            "inference_time": elapsed,
            "details": {
                "driver_status": prediction.get("driver_status", "Unknown"),
                "eye_status": prediction.get("eye_status", "Unknown"),
                "yawning_status": prediction.get("yawning_status", "Unknown"),
                "fatigue_level": prediction.get("fatigue_level", "Unknown"),
                "frames_processed": frame_count,
            },
        }


def run_live_frame(handle, frame, model_choice="model.h5"):
    """Run real-time inference on a single BGR webcam frame for Live Detection."""
    model = handle.get("model") if isinstance(handle, dict) else None
    mp_classifier = handle.get("mp_classifier") if isinstance(handle, dict) else None
    
    if model_choice == "model.h5" and model is None:
        return frame, {}
    if model_choice == "model.task" and mp_classifier is None:
        return frame, {"error": "MediaPipe model not loaded"}

    if model_choice == "model.task":
        prediction = _classify_frame_mp(mp_classifier, frame)
    else:
        prediction = _classify_frame(model, frame)
        
    annotated = _draw_status(frame.copy(), prediction)

    metrics = {
        "driver_status": prediction["driver_status"],
        "eye_status": prediction["eye_status"],
        "yawning_status": prediction["yawning_status"],
        "fatigue_level": prediction["fatigue_level"],
        "confidence": f"{prediction['confidence']}%",
        "drowsy_probability": f"{prediction['drowsy_probability']}%",
    }
    return annotated, metrics
