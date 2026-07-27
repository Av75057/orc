import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
from typing import Optional

from src.grace_api.routes import GraceAPI


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class GraceHTTPHandler(BaseHTTPRequestHandler):
    api: Optional[GraceAPI] = None

    def _send(self, status: int, headers: dict, body: bytes) -> None:
        self.send_response(status)
        for key, val in headers.items():
            self.send_header(key, val)
        for key, val in CORS_HEADERS.items():
            self.send_header(key, val)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> Optional[bytes]:
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            return self.rfile.read(length)
        return None

    def do_OPTIONS(self) -> None:
        self._send(204, {}, b"")

    def do_GET(self) -> None:
        api = self.__class__.api
        if api is None:
            self._send(500, {"Content-Type": "application/json"},
                       b'{"error":"API not initialized"}')
            return
        query = self.path.split("?", 1)[1] if "?" in self.path else ""
        path = self.path.split("?", 1)[0]
        status, headers, body = api.dispatch("GET", path, query=query)
        self._send(status, headers, body)

    def do_DELETE(self) -> None:
        api = self.__class__.api
        if api is None:
            self._send(500, {"Content-Type": "application/json"},
                       b'{"error":"API not initialized"}')
            return
        path = self.path.split("?", 1)[0]
        status, headers, body = api.dispatch("DELETE", path)
        self._send(status, headers, body)

    def do_POST(self) -> None:
        api = self.__class__.api
        if api is None:
            self._send(500, {"Content-Type": "application/json"},
                       b'{"error":"API not initialized"}')
            return
        body = self._read_body()
        path = self.path.split("?", 1)[0]
        status, headers, body = api.dispatch("POST", path, body=body)
        self._send(status, headers, body)

    def log_message(self, fmt, *args) -> None:
        sys.stderr.write(f"[GRACE-API] {args[0]} {args[1]} {args[2]}\n")


def run_server(host: str = "127.0.0.1", port: int = 8080,
               base_dir: str = ".", api_cls=GraceAPI) -> None:
    api = api_cls(base_dir=base_dir)
    GraceHTTPHandler.api = api
    class GraceHTTPServer(HTTPServer):
            allow_reuse_address = True

    server = GraceHTTPServer((host, port), GraceHTTPHandler)
    print(f"[GRACE-API] Listening on http://{host}:{port}")
    print(f"[GRACE-API] Base dir: {base_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[GRACE-API] Shutting down")
        server.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--base-dir", default=".")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, base_dir=args.base_dir)


