from __future__ import annotations

import json
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from overkill.discovery import build_overview


class DemoRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, bundle_root: Path, prompt_path: Path, **kwargs) -> None:
        self._bundle_root = bundle_root
        self._prompt_path = prompt_path
        super().__init__(*args, directory=str(Path.cwd()), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/overview":
            payload = build_overview(self._bundle_root, prompt_path=self._prompt_path)
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self._rewrite_demo_path(parsed.path)
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        self._rewrite_demo_path(parsed.path)
        super().do_HEAD()

    def _rewrite_demo_path(self, request_path: str) -> None:
        if request_path in {"/", "/demo", "/demo/"}:
            self.path = "/static/demo/index.html"
            return
        if request_path.startswith("/demo/"):
            suffix = request_path.removeprefix("/demo/")
            self.path = f"/static/demo/{suffix}"
            return
        if request_path.startswith("/data/"):
            suffix = request_path.removeprefix("/data/")
            self.path = f"/static/data/{suffix}"


def serve_demo(
    *,
    host: str,
    port: int,
    bundle_root: Path,
    prompt_path: Path,
) -> None:
    handler = partial(DemoRequestHandler, bundle_root=bundle_root, prompt_path=prompt_path)
    try:
        server = ThreadingHTTPServer((host, port), handler)
    except OSError as exc:
        raise SystemExit(f"could not bind demo server to http://{host}:{port}: {exc}") from exc
    print(f"Serving live demo on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
