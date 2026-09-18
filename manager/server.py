#!/usr/bin/env python3
"""Local-only content manager for Xin (Robynn) Shen's portfolio."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from PIL import Image, ImageOps, UnidentifiedImageError


ROOT = Path(os.environ.get("PORTFOLIO_MANAGER_ROOT", Path(__file__).resolve().parents[1])).resolve()
CONTENT_PATH = ROOT / "content" / "projects.json"
DIST_DIR = ROOT / "dist"
ASSET_DIR = DIST_DIR / "assets"
RUNTIME_DIR = ROOT / ".portfolio-manager-runtime"
BACKUP_DIR = RUNTIME_DIR / "backups"

MANAGER_HOST = "127.0.0.1"
MANAGER_PORT = int(os.environ.get("PORTFOLIO_MANAGER_PORT", "4310"))
PREVIEW_PORT = int(os.environ.get("PORTFOLIO_PREVIEW_PORT", "4173"))
TOKEN = secrets.token_urlsafe(32)

MAX_UPLOAD_BYTES = 1024 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}

SECTIONS = [
    {"value": "creative-direction", "parent": "creative", "en": "Creative Direction", "zh": "创意指导"},
    {"value": "production", "parent": "creative", "en": "Production", "zh": "制作"},
    {"value": "vibecoding", "parent": "interactive", "en": "Vibecoding", "zh": "氛围编程"},
    {"value": "mixed-reality", "parent": "vr", "en": "Mixed Reality", "zh": "混合现实"},
    {"value": "photography", "parent": "photography", "en": "Photography", "zh": "摄影"},
    {"value": "poster", "parent": "poster", "en": "Poster", "zh": "海报"},
]
SECTION_LOOKUP = {item["value"]: item for item in SECTIONS}
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

preview_server: ThreadingHTTPServer | None = None
preview_thread: threading.Thread | None = None


def read_projects() -> dict:
    with CONTENT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temporary, path)


def localized(value, fallback: str = "") -> dict:
    if isinstance(value, dict):
        return {
            "en": str(value.get("en", fallback) or fallback),
            "zh": str(value.get("zh", value.get("en", fallback)) or fallback),
        }
    if isinstance(value, str):
        return {"en": value, "zh": value}
    return {"en": fallback, "zh": fallback}


def flatten_legacy_gallery(project: dict) -> list[str]:
    if isinstance(project.get("gallery"), list):
        return [str(path) for path in project["gallery"] if isinstance(path, str) and path]

    images: list[str] = []
    for key in ("rows", "extraRows"):
        rows = project.get(key, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, list):
                images.extend(str(path) for path in row if isinstance(path, str) and path)
            elif isinstance(row, str) and row:
                images.append(row)
    return images


def cover_for(project: dict) -> str:
    cover = project.get("cover")
    if isinstance(cover, str) and cover:
        return cover
    gallery = flatten_legacy_gallery(project)
    if gallery:
        return gallery[0]
    demo = project.get("demo")
    if isinstance(demo, str) and demo:
        return demo
    videos = project.get("videos")
    if isinstance(videos, list) and videos:
        first = videos[0]
        if isinstance(first, dict) and isinstance(first.get("poster"), str):
            return first["poster"]
    return ""


def links_for(project: dict) -> list[dict]:
    links = project.get("links")
    if isinstance(links, list):
        normalized = []
        for link in links:
            if not isinstance(link, dict) or not link.get("url"):
                continue
            normalized.append({"label": localized(link.get("label"), "Open project"), "url": str(link["url"])})
        return normalized
    url = project.get("url")
    if isinstance(url, str) and url:
        return [{"label": {"en": "Open project", "zh": "打开项目"}, "url": url}]
    return []


def videos_for(project: dict) -> list[dict]:
    videos = []
    demo = project.get("demo")
    if isinstance(demo, dict) and demo.get("src"):
        videos.append({
            "src": str(demo["src"]),
            "poster": str(demo.get("poster", "")),
            "webm": str(demo.get("webm", "")),
            "title": localized(demo.get("title"), "Video"),
        })
    for video in project.get("videos", []):
        if not isinstance(video, dict) or not video.get("src"):
            continue
        videos.append({
            "src": str(video["src"]),
            "poster": str(video.get("poster", "")),
            "webm": str(video.get("webm", "")),
            "title": localized(video.get("title"), "Video"),
        })
    return videos


def year_for(project: dict) -> str:
    date = localized(project.get("date"))
    match = re.search(r"(?:19|20)\d{2}", date["en"] or date["zh"])
    return match.group(0) if match else ""


def month_for(project: dict) -> str:
    date = localized(project.get("date"))
    english = date["en"].lower()
    for index, month in enumerate(MONTHS, start=1):
        if month.lower() in english:
            return str(index)
    chinese_match = re.search(r"(?:19|20)\d{2}\s*年\s*(1[0-2]|[1-9])\s*月", date["zh"])
    return chinese_match.group(1) if chinese_match else ""


def formatted_date(year: str, month: str) -> dict:
    month_number = int(month)
    if month_number < 1 or month_number > 12:
        raise ValueError("Please choose a valid month.")
    return {"en": f"{MONTHS[month_number - 1]} {year}", "zh": f"{year} 年 {month_number} 月"}


def locate_project(data: dict, project_id: str) -> tuple[str, int, dict] | None:
    for category in data.get("categories", []):
        if not isinstance(category, dict):
            continue
        parent = category.get("id")
        entries = category.get("projects", [])
        if not isinstance(entries, list):
            continue
        for index, project in enumerate(entries):
            if isinstance(project, dict) and project.get("id") == project_id:
                return parent, index, project
    return None


def normalized_project(parent: str, project: dict) -> dict:
    section = project.get("section")
    if section not in SECTION_LOOKUP:
        section = {
            "creative": "creative-direction",
            "interactive": "vibecoding",
            "vr": "mixed-reality",
            "photography": "photography",
            "poster": "poster",
        }.get(parent, "creative-direction")
    return {
        "id": project.get("id", ""),
        "title": localized(project.get("title")),
        "year": year_for(project),
        "month": month_for(project),
        "section": section,
        "description": localized(project.get("description")),
        "cover": cover_for(project),
        "gallery": flatten_legacy_gallery(project),
        "videos": videos_for(project),
        "links": links_for(project),
    }


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "project"


def unique_project_id(data: dict, title: str) -> str:
    base = slugify(title)
    existing = {
        project.get("id")
        for category in data.get("categories", [])
        if isinstance(category, dict)
        for project in category.get("projects", [])
        if isinstance(project, dict)
    }
    candidate = base
    number = 2
    while candidate in existing:
        candidate = f"{base}-{number}"
        number += 1
    return candidate


def validate_year(value: str) -> str:
    value = str(value or "").strip()
    if not re.fullmatch(r"(?:19|20)\d{2}", value):
        raise ValueError("Year must be a four-digit year.")
    return value


def validate_links(raw_links) -> list[dict]:
    if not isinstance(raw_links, list):
        raise ValueError("Links must be a list.")
    result = []
    for link in raw_links:
        if not isinstance(link, dict):
            continue
        url = str(link.get("url", "")).strip()
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https", "mailto"}:
            raise ValueError("External links must begin with http://, https://, or mailto:.")
        label = localized(link.get("label"), "Open project")
        result.append({"label": label, "url": url})
    return result


def safe_existing_asset(value: str) -> str:
    value = str(value or "").strip().replace("\\", "/")
    if not value.startswith("assets/") or ".." in Path(value).parts:
        raise ValueError("An existing gallery path is invalid.")
    return value


def safe_existing_video(item: dict) -> dict:
    if not isinstance(item, dict):
        raise ValueError("An existing video record is invalid.")
    result = {
        "src": safe_existing_asset(item.get("src", "")),
        "poster": safe_existing_asset(item.get("poster", "")) if item.get("poster") else "",
        "title": localized(item.get("title"), "Video"),
    }
    if item.get("webm"):
        result["webm"] = safe_existing_asset(item["webm"])
    return result


def save_uploaded_image(upload, project_id: str, purpose: str) -> str:
    original_name = Path(upload.filename or "image").name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"{original_name}: please use JPG, PNG, or WebP.")

    raw = upload.read()
    if not raw:
        raise ValueError(f"{original_name}: the image is empty.")
    try:
        with Image.open(io.BytesIO(raw)) as opened:
            image = ImageOps.exif_transpose(opened)
            image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"{original_name}: the file is not a valid image.") from exc

    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")
    image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)

    encoded = io.BytesIO()
    image.save(encoded, "WEBP", quality=88, method=6)
    encoded_bytes = encoded.getvalue()
    digest = hashlib.sha256(encoded_bytes).hexdigest()[:12]
    filename = f"{slugify(purpose)}-{digest}.webp"
    project_dir = ASSET_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    destination = project_dir / filename
    if not destination.exists():
        destination.write_bytes(encoded_bytes)
    return f"assets/{project_id}/{filename}"


def save_uploaded_video(upload, project_id: str, purpose: str, title) -> dict:
    from imageio_ffmpeg import get_ffmpeg_exe

    original_name = Path(upload.filename or "video").name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValueError(f"{original_name}: please use MP4, MOV, or WebM.")

    upload_dir = RUNTIME_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temporary_input = upload_dir / f"{secrets.token_hex(12)}{extension}"
    upload.save(temporary_input)
    if not temporary_input.exists() or temporary_input.stat().st_size == 0:
        temporary_input.unlink(missing_ok=True)
        raise ValueError(f"{original_name}: the video is empty.")

    hasher = hashlib.sha256()
    with temporary_input.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()[:12]
    project_dir = ASSET_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{slugify(purpose)}-{digest}"
    destination = project_dir / f"{stem}.mp4"
    poster_destination = project_dir / f"{stem}-poster.webp"
    temporary_output = upload_dir / f"{secrets.token_hex(12)}.mp4"
    temporary_frame = upload_dir / f"{secrets.token_hex(12)}.jpg"
    ffmpeg = get_ffmpeg_exe()

    try:
        if not destination.exists():
            completed = subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(temporary_input),
                "-map", "0:v:0", "-map", "0:a:0?",
                "-vf", "scale=1280:1280:force_original_aspect_ratio=decrease:force_divisible_by=2",
                "-c:v", "libx264", "-crf", "24", "-preset", "medium", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(temporary_output),
            ], capture_output=True, text=True, timeout=900, check=False)
            if completed.returncode != 0 or not temporary_output.exists():
                raise ValueError(f"{original_name}: video processing failed. {completed.stderr.strip()}")
            os.replace(temporary_output, destination)

        if not poster_destination.exists():
            completed = subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", "0.1", "-i", str(destination),
                "-frames:v", "1", "-vf", "scale=1280:1280:force_original_aspect_ratio=decrease", str(temporary_frame),
            ], capture_output=True, text=True, timeout=120, check=False)
            if completed.returncode != 0 or not temporary_frame.exists():
                raise ValueError(f"{original_name}: poster generation failed. {completed.stderr.strip()}")
            with Image.open(temporary_frame) as frame:
                frame.convert("RGB").save(poster_destination, "WEBP", quality=86, method=6)
    finally:
        temporary_input.unlink(missing_ok=True)
        temporary_output.unlink(missing_ok=True)
        temporary_frame.unlink(missing_ok=True)

    return {
        "src": f"assets/{project_id}/{destination.name}",
        "poster": f"assets/{project_id}/{poster_destination.name}",
        "title": localized(title, Path(original_name).stem),
    }


def backup_content() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination = BACKUP_DIR / f"projects-{stamp}.json"
    shutil.copy2(CONTENT_PATH, destination)
    return destination


def portfolio_preview_url() -> str:
    return f"http://{MANAGER_HOST}:{PREVIEW_PORT}/"


def manager_origin_allowed(origin: str) -> bool:
    parsed = urlparse(origin)
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"} and parsed.port == MANAGER_PORT


@app.before_request
def protect_local_manager():
    hostname = request.host.split(":", 1)[0]
    if hostname not in {"127.0.0.1", "localhost"}:
        abort(403)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("Origin")
        if origin and not manager_origin_allowed(origin):
            abort(403)
        if request.headers.get("X-Portfolio-Token") != TOKEN:
            abort(403)


@app.get("/")
def index():
    return render_template("index.html", token=TOKEN, preview_url=portfolio_preview_url())


@app.get("/api/projects")
def projects_api():
    data = read_projects()
    projects = []
    for category in data.get("categories", []):
        if not isinstance(category, dict):
            continue
        parent = category.get("id")
        entries = category.get("projects", [])
        if not isinstance(entries, list):
            continue
        projects.extend(normalized_project(parent, project) for project in entries if isinstance(project, dict))
    return jsonify({"projects": projects, "sections": SECTIONS, "previewUrl": portfolio_preview_url()})


@app.get("/portfolio-file/<path:filename>")
def portfolio_file(filename: str):
    clean = filename.replace("\\", "/")
    if not clean.startswith("assets/") or ".." in Path(clean).parts:
        abort(404)
    return send_from_directory(DIST_DIR, clean)


@app.post("/api/projects/save")
def save_project_api():
    try:
        payload = json.loads(request.form.get("payload", "{}"))
        if not isinstance(payload, dict):
            raise ValueError("Project data is invalid.")

        data = read_projects()
        project_id = str(payload.get("id", "")).strip()
        existing_location = locate_project(data, project_id) if project_id else None
        is_new = existing_location is None

        title = localized(payload.get("title"))
        if not title["en"].strip() and not title["zh"].strip():
            raise ValueError("Please enter a project title.")
        title["en"] = title["en"].strip() or title["zh"].strip()
        title["zh"] = title["zh"].strip() or title["en"]

        year_raw = str(payload.get("year", "")).strip()
        month = str(payload.get("month", "")).strip()
        if bool(year_raw) != bool(month):
            raise ValueError("Please enter both a year and a month, or leave both blank.")
        year = validate_year(year_raw) if year_raw else ""
        if month and not re.fullmatch(r"(?:[1-9]|1[0-2])", month):
            raise ValueError("Please choose a valid month.")
        section = str(payload.get("section", ""))
        if section not in SECTION_LOOKUP:
            raise ValueError("Please choose a valid category.")
        parent = SECTION_LOOKUP[section]["parent"]

        description = localized(payload.get("description"))
        description = {key: value.strip() for key, value in description.items()}
        links = validate_links(payload.get("links", []))

        if is_new:
            project_id = unique_project_id(data, title["en"] or title["zh"])
            project = {"id": project_id}
            previous_year = ""
            previous_month = ""
        else:
            old_parent, old_index, existing = existing_location
            project = dict(existing)
            previous_year = year_for(existing)
            previous_month = month_for(existing)

        cover_upload = request.files.get("cover")
        if cover_upload and cover_upload.filename:
            project["cover"] = save_uploaded_image(cover_upload, project_id, "cover")
        elif is_new and not project.get("cover"):
            raise ValueError("A new project needs a cover image.")

        gallery_changed = bool(payload.get("galleryChanged"))
        if gallery_changed:
            ordered_gallery = payload.get("gallery", [])
            if not isinstance(ordered_gallery, list):
                raise ValueError("Gallery order is invalid.")
            new_gallery = []
            for index, item in enumerate(ordered_gallery, start=1):
                if not isinstance(item, dict):
                    continue
                kind = item.get("kind")
                if kind == "existing":
                    new_gallery.append(safe_existing_asset(item.get("path", "")))
                elif kind == "new":
                    key = str(item.get("key", ""))
                    upload = request.files.get(f"gallery_{key}")
                    if not upload or not upload.filename:
                        raise ValueError("A selected gallery image could not be read.")
                    new_gallery.append(save_uploaded_image(upload, project_id, f"gallery-{index:02d}"))
            project["gallery"] = new_gallery

        videos_changed = bool(payload.get("videosChanged"))
        if videos_changed:
            ordered_videos = payload.get("videos", [])
            if not isinstance(ordered_videos, list):
                raise ValueError("Video order is invalid.")
            new_videos = []
            for index, item in enumerate(ordered_videos, start=1):
                if not isinstance(item, dict):
                    continue
                if item.get("kind") == "existing":
                    video = safe_existing_video(item)
                    video["title"] = localized(item.get("title"), "Video")
                    new_videos.append(video)
                elif item.get("kind") == "new":
                    key = str(item.get("key", ""))
                    upload = request.files.get(f"video_{key}")
                    if not upload or not upload.filename:
                        raise ValueError("A selected video could not be read.")
                    new_videos.append(save_uploaded_video(upload, project_id, f"video-{index:02d}", item.get("title")))
            project.pop("demo", None)
            project["videos"] = new_videos

        project["id"] = project_id
        project["title"] = title
        if is_new or year != previous_year or month != previous_month:
            project["date"] = formatted_date(year, month) if year and month else {"en": "", "zh": ""}
        project["section"] = section
        project["description"] = description
        project["links"] = links
        if is_new:
            project["discipline"] = {"en": SECTION_LOOKUP[section]["en"], "zh": SECTION_LOOKUP[section]["zh"]}

        backup = backup_content()
        categories = data.setdefault("categories", [])
        target_category = next((item for item in categories if isinstance(item, dict) and item.get("id") == parent), None)
        if target_category is None:
            raise ValueError("The selected portfolio category does not exist.")
        target_projects = target_category.setdefault("projects", [])
        if is_new:
            target_projects.append(project)
        else:
            if old_parent == parent:
                target_projects[old_index] = project
            else:
                old_category = next((item for item in categories if isinstance(item, dict) and item.get("id") == old_parent), None)
                if old_category is None:
                    raise ValueError("The project's original category could not be found.")
                old_category.get("projects", []).pop(old_index)
                target_projects.append(project)
        atomic_write_json(CONTENT_PATH, data)

        return jsonify({
            "ok": True,
            "message": "Project saved. Build the portfolio when you are ready to preview it.",
            "project": normalized_project(parent, project),
            "backup": backup.name,
        })
    except (ValueError, json.JSONDecodeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/projects/delete")
def delete_project_api():
    try:
        payload = request.get_json(silent=True) or {}
        project_id = str(payload.get("id", "")).strip()
        if not project_id:
            raise ValueError("No project was selected.")
        data = read_projects()
        location = locate_project(data, project_id)
        if location is None:
            raise ValueError("The project could not be found.")
        parent, index, project = location
        backup = backup_content()
        category = next(item for item in data.get("categories", []) if isinstance(item, dict) and item.get("id") == parent)
        category.get("projects", []).pop(index)
        atomic_write_json(CONTENT_PATH, data)
        return jsonify({
            "ok": True,
            "message": "Project removed from the portfolio. Its media files were kept. Build the portfolio to update the preview.",
            "deletedTitle": localized(project.get("title")),
            "backup": backup.name,
        })
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/build")
def build_api():
    try:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "update_content.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout or "Build failed.").strip()
            return jsonify({"ok": False, "error": details}), 500
        valid_project_pages = {
            f"project-{project.get('id')}.html"
            for category in read_projects().get("categories", [])
            if isinstance(category, dict)
            for project in category.get("projects", [])
            if isinstance(project, dict) and project.get("id") and project.get("section") not in {"photography", "poster"}
        }
        for page_path in DIST_DIR.glob("project-*.html"):
            if page_path.name not in valid_project_pages:
                page_path.unlink()
        start_preview_server()
        return jsonify({
            "ok": True,
            "message": "Portfolio built successfully. Local Preview is ready.",
            "previewUrl": portfolio_preview_url(),
            "output": completed.stdout.strip(),
        })
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "The build took too long and was stopped."}), 500


@app.get("/api/status")
def status_api():
    return jsonify({"ok": True, "previewUrl": portfolio_preview_url(), "previewRunning": port_is_open(PREVIEW_PORT)})


def port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((MANAGER_HOST, port)) == 0


def start_preview_server() -> bool:
    global preview_server, preview_thread
    if port_is_open(PREVIEW_PORT):
        return False

    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(DIST_DIR), **kwargs)

        def log_message(self, _format, *args):
            return

    preview_server = ThreadingHTTPServer((MANAGER_HOST, PREVIEW_PORT), QuietHandler)
    preview_thread = threading.Thread(target=preview_server.serve_forever, daemon=True)
    preview_thread.start()
    return True


def open_manager_when_ready() -> None:
    time.sleep(0.8)
    webbrowser.open(f"http://{MANAGER_HOST}:{MANAGER_PORT}/")


if __name__ == "__main__":
    start_preview_server()
    if os.environ.get("PORTFOLIO_MANAGER_NO_BROWSER") != "1":
        threading.Thread(target=open_manager_when_ready, daemon=True).start()
    print(f"Portfolio Manager: http://{MANAGER_HOST}:{MANAGER_PORT}/")
    print(f"Portfolio Preview: {portfolio_preview_url()}")
    print("Keep this window open while using the Manager. Press Control-C to stop.")
    app.run(host=MANAGER_HOST, port=MANAGER_PORT, debug=False, use_reloader=False)
