"""
utils/model_loader.py
----------------------
Loads every AI model ONCE when Flask starts and keeps the handle in memory
for the lifetime of the process. Services pull model handles from here --
they never touch models/ directly and never reload weights per-request.

Each model directory under models/<module>/ is expected to already contain
model.pt and inference.py exactly as described in the project brief. This
loader does not train, download, or modify any weight file -- it only
imports each module's inference entrypoint and, if available, calls its
`load_model(weights_path)` function to warm the model into memory.

If a given model's inference.py does not yet expose a `load_model`
function (e.g. during early integration before the CV engineer has wired
it up), the loader degrades gracefully and the corresponding service falls
back to its offline-safe simulation path -- this keeps the rest of the
platform fully demonstrable even before every model is dropped in.
"""

import importlib.util
import os
import sys
import time

from config import Config

_LOADED_MODELS = {}
_LOAD_STATUS = {}


def _import_inference_module(module_key, module_dir):
    """Dynamically import models/<module_dir>/inference.py as a module."""
    inference_path = os.path.join(module_dir, "inference.py")
    if not os.path.isfile(inference_path):
        return None

    spec_name = f"roadsense_inference_{module_key}"
    spec = importlib.util.spec_from_file_location(spec_name, inference_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec_name] = module
    spec.loader.exec_module(module)
    return module


def load_all_models():
    """
    Called once from app.py at startup. Walks the MODEL_REGISTRY, imports
    each module's inference.py, and warms its model into memory via
    load_model() when that hook exists.
    """
    for module_key, meta in Config.MODEL_REGISTRY.items():
        start = time.time()
        status = {
            "loaded": False,
            "name": meta["name"],
            "weights_found": os.path.isfile(meta["weights"]),
            "inference_found": os.path.isfile(os.path.join(meta["dir"], "inference.py")),
            "error": None,
        }

        try:
            inference_module = _import_inference_module(module_key, meta["dir"])
            if inference_module is not None and hasattr(inference_module, "load_model"):
                handle = inference_module.load_model(meta["weights"])
                _LOADED_MODELS[module_key] = {
                    "module": inference_module,
                    "handle": handle,
                }
                status["loaded"] = True
            elif inference_module is not None:
                # inference.py exists but has no explicit load_model hook --
                # keep the module reference so services can still call a
                # run/predict-style function directly if one is exposed.
                _LOADED_MODELS[module_key] = {
                    "module": inference_module,
                    "handle": None,
                }
                status["loaded"] = True
        except Exception as exc:  # noqa: BLE001 - surfaced in System Status UI
            status["error"] = str(exc)

        status["load_time"] = round(time.time() - start, 3)
        _LOAD_STATUS[module_key] = status

    return _LOAD_STATUS


def get_model(module_key):
    """Return the loaded {module, handle} dict for a module, or None."""
    return _LOADED_MODELS.get(module_key)


def get_status(module_key=None):
    """Return load status for one module, or all modules if key is None."""
    if module_key:
        return _LOAD_STATUS.get(module_key)
    return _LOAD_STATUS
