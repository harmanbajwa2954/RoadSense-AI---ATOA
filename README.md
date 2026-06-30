---
title: RoadSense AI
emoji: 📚
colorFrom: yellow
colorTo: red
sdk: docker
pinned: false
short_description: RoadSense
---

# RoadSense AI

**An Offline AI-Powered Traffic Intelligence & Driver Assistance Platform**

A Flask-based command center that unifies five independent computer-vision
modules — lane detection, traffic sign recognition, road surface
(pothole) inspection, emergency vehicle detection, and driver drowsiness
detection — into one professional, fully-offline platform.

---

## 1. Quick Start

```bash
# from the project root
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

The app will:
- create `database/roadsense.db` and seed it with a few demo incidents and
  analysis-history rows (first run only)
- create any missing `uploads/` and `outputs/` subfolders
- load every model in `models/` **once**, into memory, and print a status
  table to the console

No internet connection is required after the page's Google Fonts and
Chart.js CDN links are first cached by the browser — everything else
(inference, storage, routing) runs entirely on `localhost`.

---

## 2. Plugging In Your Real Models

Every module directory under `models/` currently ships with a
**placeholder** `model.pt` and a working `inference.py` stub so the whole
platform is demonstrable out of the box. To wire in your real, trained
model:

1. Replace `models/<module>/model.pt` with your real weights file.
2. Open `models/<module>/inference.py` and replace the body of
   `load_model()` and `run_inference()` with your real pipeline. **Keep
   both function signatures unchanged** — that's the contract the rest of
   the app relies on:

   ```python
   def load_model(weights_path):
       # called once at Flask startup
       ...
       return handle

   def run_inference(handle, media_path, media_type, output_dir):
       # called once per analysis request
       ...
       return {
           "annotated_path": "<path to annotated image/video you wrote into output_dir>",
           "confidence": 92.4,
           "objects_detected": 3,
           "inference_time": 0.41,
           "details": { ... }  # module-specific fields shown in the UI
       }
   ```

3. That's it — no route, service, or template changes are needed. The
   service layer (`services/*.py`) and the model loader
   (`utils/model_loader.py`) already call into this exact interface.

---

## 3. Architecture

```
Browser
   |
   v
Routes (routes/*.py)        - thin Flask Blueprints, no business logic
   |
   v
Services (services/*.py)    - orchestration, DB logging, normalization
   |
   v
Model Inference (models/*)  - your inference.py, loaded once at startup
   |
   v
Results -> rendered in templates/ or returned as JSON to the frontend JS
```

Routes never import from `models/` or `utils/model_loader` directly —
they only ever call into a `services/*_service.py` function. This keeps
every module independently swappable.

### Lazy execution in the Analysis Workspace

The Workspace page (`/workspace`) has **one** upload section. After a file
is uploaded, nothing is processed until the user clicks a tab. Each tab
(Lane / Traffic Sign / Road Surface / Emergency) calls its own
`/api/analyze/...` endpoint, which runs only that module's model. Results
are cached client-side per tab for the current upload, so re-opening a tab
doesn't re-run inference.

### Driver Monitoring

`/driver-monitoring` is intentionally separate from the Workspace — its
own upload, its own endpoint (`/api/drowsiness/upload-and-analyze`), and it
only ever touches the drowsiness model.

### Live Detection Lab

`/live-detection` renders one card per module. Each card starts/stops its
own webcam feed independently — there is no shared or unified live
pipeline, by design.

---

## 4. Project Structure

```
RoadSenseAI/
├── app.py                  # entrypoint: config, DB init, model warm-up, blueprints
├── config.py                # all paths, upload limits, model registry
├── requirements.txt
├── routes/                  # Flask Blueprints (one file per page/concern)
├── services/                 # business logic between routes and models
├── models/                   # your AI models — model.pt + inference.py per module
├── database/                 # roadsense.db (SQLite, created on first run)
├── uploads/ / outputs/        # per-module temp storage, created on first run
├── static/css|js/             # design tokens, components, page styles, page scripts
├── templates/                 # Jinja2 templates, inherit from base.html
└── utils/                     # db.py, file_utils.py, model_loader.py
```

---

## 5. Notes for the Viva

- Everything in this repo runs **fully offline** — no external API calls
  are made at inference time. Chart.js and Google Fonts are loaded from a
  CDN purely for styling/charting and are not required for any AI feature
  to function; if you need a 100% air-gapped demo, vendor those two files
  locally before presenting.
- The seeded incidents and analysis-history rows in SQLite exist only so
  the dashboard and Incident Monitoring pages aren't empty on a cold boot;
  delete `database/roadsense.db` at any time to reset to a clean slate.
- Analytics charts use clearly-labeled demo data per the original brief;
  swap `services/dashboard_service.get_analytics_data()` for real
  aggregation queries once enough live history has accumulated.
