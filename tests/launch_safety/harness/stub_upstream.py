"""Tiny deterministic upstreams for the Nginx maintenance integration harness."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from urllib.parse import urlsplit


class StubHandler(BaseHTTPRequestHandler):
    server_version = "vl360-maintenance-stub/1.0"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlsplit(self.path).path
        if path.startswith("/_internal/"):
            self.send_response(404)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return

        port = self.server.server_port
        body = f"stub-upstream:{port}:{path}\n".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex, follow")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def serve(port: int) -> None:
    ThreadingHTTPServer(("0.0.0.0", port), StubHandler).serve_forever()


def main() -> None:
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
