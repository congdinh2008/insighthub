"""Bounded Day 04 provider proxy: normal pass-through, latency or 503."""

import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UPSTREAM = os.environ["UPSTREAM_ORIGIN"].rstrip("/")
CONFIG = Path("/fault-config")
MAX_BODY = 2 * 1024 * 1024


def read_mode() -> tuple[str, float]:
    mode = (CONFIG / "mode").read_text().strip()
    if mode not in {"normal", "latency", "error"}:
        raise ValueError("unsupported fault mode")
    delay = float((CONFIG / "delay-seconds").read_text().strip())
    if not 0 <= delay <= 10:
        raise ValueError("delay must be between 0 and 10 seconds")
    return mode, delay


class Proxy(BaseHTTPRequestHandler):
    server_version = "InsightHubDay4Proxy/1.0"

    def log_message(self, format_string: str, *args: object) -> None:
        print(
            json.dumps(
                {"event": "provider_proxy", "path": self.path, "status": args[1]},
                separators=(",", ":"),
            ),
            flush=True,
        )

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        self.forward()

    def do_POST(self) -> None:
        self.forward()

    def forward(self) -> None:
        mode, delay = read_mode()
        if mode == "latency":
            time.sleep(delay)
        if mode == "error":
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"day4 injected failure"}}')
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > MAX_BODY:
            self.send_error(413)
            return
        body = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "content-length", "connection"}
        }
        request = urllib.request.Request(
            UPSTREAM + self.path,
            data=body,
            headers=headers,
            method=self.command,
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload, status, response_headers = (
                    response.read(MAX_BODY + 1),
                    response.status,
                    response.headers,
                )
        except urllib.error.HTTPError as error:
            payload, status, response_headers = (
                error.read(MAX_BODY + 1),
                error.code,
                error.headers,
            )
        if len(payload) > MAX_BODY:
            self.send_error(502)
            return
        self.send_response(status)
        if response_headers.get("Content-Type"):
            self.send_header("Content-Type", response_headers["Content-Type"])
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


ThreadingHTTPServer(("0.0.0.0", 8080), Proxy).serve_forever()
