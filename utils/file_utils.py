"""
utils/file_utils.py
--------------------
Shared filesystem helpers: extension checks, safe filenames, media-type
detection, and cleanup of temporary uploads/outputs.
"""

import os
import time
import uuid

from werkzeug.utils import secure_filename

from config import Config


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in Config.ALLOWED_IMAGE_EXT or ext in Config.ALLOWED_VIDEO_EXT


def get_media_type(filename):
    """Return 'image', 'video', or None based on extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in Config.ALLOWED_IMAGE_EXT:
        return "image"
    if ext in Config.ALLOWED_VIDEO_EXT:
        return "video"
    return None


def save_workspace_upload(file_storage):
    """
    Save an Analysis Workspace upload to the shared workspace holding
    directory under a unique, collision-proof name.

    Returns (saved_filename, absolute_path, media_type).
    """
    original = secure_filename(file_storage.filename)
    if not original or not allowed_file(original):
        raise ValueError("Unsupported file type.")

    ext = original.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex[:10]}.{ext}"
    dest_path = os.path.join(Config.WORKSPACE_UPLOAD_DIR, unique_name)

    os.makedirs(Config.WORKSPACE_UPLOAD_DIR, exist_ok=True)
    file_storage.save(dest_path)

    return unique_name, dest_path, get_media_type(original)


def save_module_upload(file_storage, module_key):
    """
    Save an upload directly into a module-specific upload directory
    (used by Driver Monitoring, which has its own dedicated upload flow).
    """
    original = secure_filename(file_storage.filename)
    if not original or not allowed_file(original):
        raise ValueError("Unsupported file type.")

    ext = original.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex[:10]}.{ext}"
    dest_dir = Config.UPLOAD_DIRS[module_key]
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, unique_name)
    file_storage.save(dest_path)

    return unique_name, dest_path, get_media_type(original)


def cleanup_stale_files(directory, max_age_seconds=3600):
    """Delete files older than max_age_seconds from a directory."""
    if not os.path.isdir(directory):
        return
    now = time.time()
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        try:
            if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > max_age_seconds:
                os.remove(fpath)
        except OSError:
            pass
