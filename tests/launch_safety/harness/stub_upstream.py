"""Tiny deterministic upstreams for the Nginx maintenance integration harness."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from urllib.parse import urlsplit


def response_for(port: int, path: str) -> tuple[int, dict[str, str], bytes]:
    if path.startswith("/_internal/"):
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

    body = f"stub-upstream:{port}:{path}\n".encode("utf-8")
    return (
        200,
        {
            "Cache-Control": "no-store",
            "Content-Type": "text/plain; charset=utf-8",
            "X-Robots-Tag": "noindex, follow",
        },
        body,
    )


class StubHandler(BaseHTTPRequestHandler):
    server_version = "vl360-maintenance-stub/1.0"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlsplit(self.path).path
        status, headers, body = response_for(self.server.server_port, path)
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers.items():
            self.send_header(name, value)
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
