"""Minimal HTTP server that receives labeling POST requests and persists them to
results/validations/labels.json.

Usage:
    uv run python scripts/label_server.py [--labels results/validations/labels.json] [--port 8123]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DEFAULT_LABELS_PATH = Path("results/validations/labels.json")
DEFAULT_PORT = 8123


def _load_labels(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logging.warning("Could not parse %s — starting fresh", path)
    return {}


def _save_labels(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def make_handler(labels_path: Path):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # suppress default access log; use our logger
            logging.info(fmt, *args)

        def _send_json(self, code: int, body: dict) -> None:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            # CORS — allow the file:// origin when the report is opened locally
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(payload)

        def do_OPTIONS(self):
            """Handle CORS preflight."""
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_POST(self):
            if self.path != "/save":
                self._send_json(404, {"error": "not found"})
                return

            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                self._send_json(400, {"error": "empty body"})
                return

            raw = self.rfile.read(length)
            try:
                incoming: dict = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                self._send_json(400, {"error": f"invalid JSON: {exc}"})
                return

            if not isinstance(incoming, dict):
                self._send_json(400, {"error": "expected JSON object"})
                return

            # Merge with existing labels
            existing = _load_labels(labels_path)
            for rank_str, site_labels in incoming.items():
                if not isinstance(site_labels, dict):
                    continue
                if rank_str not in existing:
                    existing[rank_str] = {}
                existing[rank_str].update(site_labels)

            try:
                _save_labels(labels_path, existing)
            except Exception as exc:
                self._send_json(500, {"error": f"write failed: {exc}"})
                return

            logging.info("Saved labels for ranks: %s", list(incoming.keys()))
            self._send_json(200, {"ok": True, "saved": existing})

    return _Handler


def main() -> None:
    p = argparse.ArgumentParser(description="Label server for audit report")
    p.add_argument(
        "--labels",
        default=str(DEFAULT_LABELS_PATH),
        help=f"Path to labels.json (default: {DEFAULT_LABELS_PATH})",
    )
    p.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    args = p.parse_args()

    labels_path = Path(args.labels)
    port = args.port

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )

    handler_class = make_handler(labels_path)
    httpd = HTTPServer(("", port), handler_class)
    logging.info("Label server listening on http://localhost:%d/save", port)
    logging.info("Labels will be persisted to: %s", labels_path.resolve())
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server stopped.")


if __name__ == "__main__":
    main()
