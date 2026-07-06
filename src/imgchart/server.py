import json
import os
import re
import struct
import tempfile
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

UPLOAD_DIR = Path(os.environ.get("IMGCHART_DIR", r"C:\imgchart"))
MAX_BYTES = int(os.environ.get("IMGCHART_MAX_BYTES", str(50 * 1024 * 1024)))
MIN_BYTES = int(os.environ.get("IMGCHART_MIN_BYTES", str(5 * 1024)))
MIN_WIDTH = int(os.environ.get("IMGCHART_MIN_WIDTH", "320"))
MIN_HEIGHT = int(os.environ.get("IMGCHART_MIN_HEIGHT", "180"))
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
WALLBOARD_URL = os.environ.get("IMGCHART_WALLBOARD_URL", "https://airdapp.airewardrop.xyz/wallboard")
DISPLAY_SECONDS = int(os.environ.get("IMGCHART_DISPLAY_SECONDS", "10"))
TRANSPARENT_PNG_PATH = Path(os.environ.get("IMGCHART_TRANSPARENT_PNG", r"C:\ImgChartUpload\transparent.png"))
WALLBOARD_IMAGE_PATH = Path(os.environ.get("IMGCHART_WALLBOARD_IMAGE", r"C:\ImgChartUpload\wallboard.png"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")

MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
}


def safe_name(name: str) -> str:
    name = Path(name or "image.bin").name
    name = _SAFE.sub("_", name).strip("._") or "image.bin"
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"Unsupported extension: {ext or '(none)'}")
    return name


def image_files():
    return [p for p in UPLOAD_DIR.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED_EXT and not p.name.startswith("upload_")]


def latest_image():
    files = image_files()
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def inspect_image(data: bytes) -> tuple[str, int, int]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if len(data) < 24:
            raise ValueError("PNG too short")
        width, height = struct.unpack(">II", data[16:24])
        return "png", width, height
    if data.startswith(b"\xff\xd8"):
        pos = 2
        while pos + 9 < len(data):
            if data[pos] != 0xFF:
                pos += 1
                continue
            marker = data[pos + 1]
            if marker in (0xC0, 0xC2):
                height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
                return "jpeg", width, height
            if pos + 4 > len(data):
                break
            segment_length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
            if segment_length < 2:
                break
            pos += 2 + segment_length
        raise ValueError("JPEG dimensions not found")
    raise ValueError("unsupported or invalid image signature")


def validate_upload(data: bytes) -> tuple[str, int, int]:
    if len(data) < MIN_BYTES:
        raise ValueError(f"image too small: {len(data)} bytes < {MIN_BYTES}")
    kind, width, height = inspect_image(data)
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        raise ValueError(f"image dimensions too small: {width}x{height} < {MIN_WIDTH}x{MIN_HEIGHT}")
    return kind, width, height


def base_image_bytes():
    if WALLBOARD_IMAGE_PATH.exists():
        return WALLBOARD_IMAGE_PATH.read_bytes()
    return TRANSPARENT_PNG_PATH.read_bytes()


def viewer_html():
    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <title>ImgChart Wallboard</title>
  <style>
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: #000; }}
    #wallboard, #chart {{ position: fixed; inset: 0; width: 100vw; height: 100vh; border: 0; }}
    #wallboard {{ z-index: 1; }}
    #chart {{ z-index: 2; object-fit: contain; background: #000; display: none; visibility: hidden; opacity: 0; transition: opacity 180ms linear; }}
    #chart.visible {{ display: block; visibility: visible; opacity: 1; }}
  </style>
</head>
<body>
  <iframe id=\"wallboard\" src=\"{WALLBOARD_URL}\" allow=\"fullscreen; autoplay\"></iframe>
  <img id=\"chart\" alt=\"latest chart\">
  <script>
    const POLL_MS = 1000;
    const DISPLAY_MS = {DISPLAY_SECONDS * 1000};
    const chart = document.getElementById('chart');
    let lastKey = null;
    let hideTimer = null;

    async function poll() {{
      try {{
        const res = await fetch('/latest?ts=' + Date.now(), {{cache: 'no-store'}});
        if (!res.ok) return;
        const data = await res.json();
        if (!data.ok || !data.file) {{
          chart.classList.remove('visible');
          chart.removeAttribute('src');
          return;
        }}
        const key = data.file + ':' + data.mtime_ns + ':' + data.size;
        if (key === lastKey) return;
        lastKey = key;
        chart.onload = () => {{
          chart.classList.add('visible');
          clearTimeout(hideTimer);
          hideTimer = setTimeout(() => {{
            chart.classList.remove('visible');
            chart.removeAttribute('src');
          }}, DISPLAY_MS);
        }};
        chart.src = data.url + '?v=' + encodeURIComponent(key);
      }} catch (e) {{}}
    }}

    setInterval(poll, POLL_MS);
    poll();
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "ImgChartUpload/1.1"

    def log_message(self, fmt, *args):
        print(f"{datetime.now().isoformat()} {self.client_address[0]} {fmt % args}", flush=True)

    def _send(self, code, body, content_type="application/json", cache=False):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if not cache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._send(200, viewer_html(), "text/html; charset=utf-8")
            return
        if path == "/health":
            files = sorted(image_files(), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
            self._send(200, {"ok": True, "dir": str(UPLOAD_DIR), "latest": [p.name for p in files]})
            return
        if path == "/latest":
            img = latest_image()
            if not img or time.time() - img.stat().st_mtime > DISPLAY_SECONDS:
                self._send(200, {"ok": True, "file": None})
                return
            st = img.stat()
            self._send(200, {"ok": True, "file": img.name, "url": "/image/" + quote(img.name), "mtime": st.st_mtime, "mtime_ns": st.st_mtime_ns, "size": st.st_size})
            return
        if path in ("/img/default.jpg", "/img/default.png"):
            self._send(200, base_image_bytes(), "image/png", cache=False)
            return
        if path in ("/img/latest.jpg", "/img/latest.png", "/latest.jpg", "/latest.png"):
            img = latest_image()
            if not img or time.time() - img.stat().st_mtime > DISPLAY_SECONDS:
                self._send(200, base_image_bytes(), "image/png", cache=False)
                return
            data = img.read_bytes()
            self._send(200, data, MIME.get(img.suffix.lower(), "image/jpeg"), cache=False)
            return
        if path.startswith("/image/"):
            try:
                name = safe_name(unquote(path.removeprefix("/image/")))
                img = UPLOAD_DIR / name
                if not img.exists() or not img.is_file():
                    self._send(404, {"ok": False, "error": "not found"})
                    return
                data = img.read_bytes()
                self._send(200, data, MIME.get(img.suffix.lower(), "application/octet-stream"), cache=False)
            except Exception as exc:
                self._send(400, {"ok": False, "error": str(exc)})
            return
        self._send(404, {"ok": False, "error": "not found"})

    def do_PUT(self):
        try:
            qs = parse_qs(urlparse(self.path).query)
            raw_name = qs.get("filename", [Path(urlparse(self.path).path).name])[0]
            name = safe_name(raw_name)
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BYTES:
                self._send(413, {"ok": False, "error": "invalid size"})
                return
            target = UPLOAD_DIR / name
            fd, tmp = tempfile.mkstemp(prefix="upload_", suffix=target.suffix, dir=str(UPLOAD_DIR))
            try:
                with os.fdopen(fd, "wb") as f:
                    remaining = length
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise RuntimeError("client disconnected")
                        f.write(chunk)
                        remaining -= len(chunk)
                data = Path(tmp).read_bytes()
                kind, width, height = validate_upload(data)
                os.replace(tmp, target)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            self._send(201, {"ok": True, "file": target.name, "bytes": length, "kind": kind, "width": width, "height": height})
        except Exception as exc:
            self._send(400, {"ok": False, "error": str(exc)})

    def do_POST(self):
        self.do_PUT()


if __name__ == "__main__":
    host = os.environ.get("IMGCHART_HOST", "127.0.0.1")
    port = int(os.environ.get("IMGCHART_PORT", "8890"))
    print(f"ImgChart upload/viewer server on http://{host}:{port} -> {UPLOAD_DIR}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


