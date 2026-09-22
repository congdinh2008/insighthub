"""A bounded Docker API read view for the single Day 02 Compose project.

The MCP Gateway never receives the engine socket. This helper does not implement
MCP: it enforces the lab's Docker API policy below the upstream Docker CLI.
"""

import http.client
import json
import os
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

PROJECT = os.environ.get("COMPOSE_PROJECT_NAME", "insighthub-day2-lab")
MAX_BYTES = 131072
SLOTS = threading.BoundedSemaphore(4)
SOCKET_PATH = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect(SOCKET_PATH)


def upstream(route):
    connection = UnixConnection("localhost", timeout=3)
    try:
        connection.request("GET", route)
        response = connection.getresponse()
        data = response.read(MAX_BYTES + 1)
        if response.status != 200 or len(data) > MAX_BYTES:
            raise ValueError("Upstream rejected or exceeded response limit")
        return data
    finally:
        connection.close()


def allowed_route(raw):
    split = urlsplit(raw)
    path = re.sub(r"^/v[0-9]+\.[0-9]+", "", split.path)
    query = parse_qs(split.query, keep_blank_values=True)
    if path in {"/_ping", "/version"} and not query:
        return path, "version"
    if path == "/containers/json":
        # Caller filters cannot broaden the fixed project filter.
        if set(query) - {"all", "filters", "limit", "size"}:
            raise PermissionError("Unsupported query")
        return "/containers/json?" + urlencode(
            {
                "all": "1",
                "filters": json.dumps(
                    {"label": [f"com.docker.compose.project={PROJECT}"]}
                ),
            }
        ), "list"
    match = re.fullmatch(r"/containers/([a-z0-9-]+)/(json|logs)", path)
    allowed_names = {f"{PROJECT}-debug-case-1", f"{PROJECT}-ingestion-worker-1"}
    container_name = match[1] if match else None
    if match and re.fullmatch(r"[a-f0-9]{64}", match[1]):
        metadata = json.loads(upstream(f"/containers/{match[1]}/json"))
        if (
            metadata.get("Config", {})
            .get("Labels", {})
            .get("com.docker.compose.project")
            == PROJECT
        ):
            container_name = metadata.get("Name", "").lstrip("/")
    if match and container_name in allowed_names:
        path = f"/containers/{container_name}/{match[2]}"
        if match[2] == "json" and not query:
            return path, "inspect"
        if match[2] == "logs" and not (
            set(query) - {"stdout", "stderr", "tail", "timestamps", "follow"}
        ):
            if query.get("follow", ["0"])[0] not in {"0", "false"}:
                raise PermissionError("Streaming not enabled")
            return path + "?stdout=1&stderr=1&tail=100&timestamps=1", "logs"
    raise PermissionError("Route outside Day 02 read scope")


def project_response(data, kind):
    if kind in {"version", "logs"}:
        return data
    value = json.loads(data)
    if kind == "list":
        fields = (
            "Id",
            "Names",
            "Image",
            "ImageID",
            "Created",
            "State",
            "Status",
            "Ports",
        )
        value = [{k: row[k] for k in fields if k in row} for row in value[:20]]
    elif kind == "inspect":
        value = {
            "Id": value["Id"],
            "Name": value["Name"],
            "Config": {"Tty": value["Config"]["Tty"]},
            "State": {
                k: value["State"].get(k) for k in ("Status", "Running", "ExitCode")
            },
        }
    return json.dumps(value).encode()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass  # Do not log model arguments or daemon responses.

    def send_body(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Api-Version", "1.54")
        self.send_header("Docker-Experimental", "false")
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        self.close_connection = True

    def do_GET(self):
        if not SLOTS.acquire(blocking=False):
            self.send_body(429, b'{"message":"Busy"}')
            return
        try:
            route, kind = allowed_route(self.path)
            body = (
                b"OK" if route == "/_ping" else project_response(upstream(route), kind)
            )
            self.send_body(200, body)
        except PermissionError:
            print(
                json.dumps(
                    {
                        "event": "docker_read_denied",
                        "method": self.command,
                        "query_keys": sorted(parse_qs(urlsplit(self.path).query)),
                        "route_kind": urlsplit(self.path).path.rsplit("/", 1)[-1][:30],
                    }
                ),
                flush=True,
            )
            self.send_body(403, b'{"message":"Outside Day 02 read scope"}')
        except (OSError, ValueError, KeyError, http.client.HTTPException):
            self.send_body(502, b'{"message":"Docker read unavailable"}')
        finally:
            SLOTS.release()

    def do_HEAD(self):
        if self.path != "/_ping":
            self.deny()
            return
        self.do_GET()

    def deny(self):
        self.send_body(403, b'{"message":"Read-only Docker view"}')

    do_POST = deny
    do_DELETE = deny
    do_PUT = deny
    do_PATCH = deny


if __name__ == "__main__":
    if not re.fullmatch(r"insighthub-day2-[a-z0-9-]+", PROJECT):
        raise SystemExit("Explicit Day 02 project required")
    ThreadingHTTPServer(("0.0.0.0", 2375), Handler).serve_forever()
