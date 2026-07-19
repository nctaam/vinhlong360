"""Tiny deterministic upstreams for the Nginx maintenance integration harness."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from urllib.parse import urlsplit


def response_for(port: int, path: str, role: str | None = None) -> tuple[int, dict[str, str], bytes]:
    request_path = urlsplit(path).path
    label = f"stub-{role}-upstream" if role else "stub-upstream"
    if request_path.startswith("/_internal/"):
        body = f"stub-internal-upstream:{port}:{path}\n".encode("utf-8")
        return (
            418,
            {
                "Cache-Control": "no-store",
                "Content-Type": "text/plain; charset=utf-8",
                "X-VL360-Upstream-Internal": "reached",
            },
            body,
        )

    headers = {
        "Cache-Control": "no-store",
        "Content-Type": "text/plain; charset=utf-8",
        "X-Robots-Tag": "noindex, follow",
    }
    if role == "nuxt":
        headers["X-Launch-Indexing-Policy"] = "failed-open"
        headers["X-Launch-Route-Manifest-Revision"] = "stub-route-v1"
    body = f"{label}:{port}:{path}\n".encode("utf-8")
    return (200, headers, body)


class StubHandler(BaseHTTPRequestHandler):
    server_version = "vl360-maintenance-stub/1.0"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        role = getattr(self.server, "stub_role", None)
        status, headers, body = response_for(self.server.server_port, self.path, role)
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def serve(port: int, role: str | None = None) -> None:
    server = ThreadingHTTPServer(("0.0.0.0", port), StubHandler)
    server.stub_role = role
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int)
    parser.add_argument("--role")
    args = parser.parse_args()
    if args.port is not None:
        serve(args.port, args.role)
        return
    threads = [
        threading.Thread(target=serve, args=(port,), daemon=True)
        for port in (3000, 8360, 8361)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
