"""Self-contained local test site; only synthetic images, no external services."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import math
import secrets
import threading
from urllib.parse import urlsplit

from .synthetic import puzzle


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        super().__init__(address,DemoHandler)
        self.challenges = {}
        self.guard = threading.Lock()


class DemoHandler(BaseHTTPRequestHandler):
    def log_message(self,*_):
        pass

    def respond(self,body,status=200,content_type="application/json; charset=utf-8"):
        body = body if isinstance(body,bytes) else json.dumps(body,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            return self.respond(files("slider_captcha_kit").joinpath("assets/demo.html").read_bytes(),content_type="text/html; charset=utf-8")
        if path == "/challenge":
            offset = 70+secrets.randbelow(220)
            bg,piece,meta = puzzle(offset=offset,seed=secrets.randbelow(1_000_000))
            key = secrets.token_hex(12)
            with self.server.guard:
                if len(self.server.challenges) >= 256:
                    self.server.challenges.pop(next(iter(self.server.challenges)))
                self.server.challenges[key] = (offset,bg,piece)
            encode = lambda b: "data:image/png;base64,"+base64.b64encode(b).decode()
            return self.respond({"id":key,"background":encode(bg),"piece":encode(piece)})
        if path.startswith("/image/"):
            parts = path.strip("/").split("/")
            if len(parts)==3 and parts[2] in {"background.png","piece.png"}:
                with self.server.guard:
                    challenge = self.server.challenges.get(parts[1])
                if challenge:
                    return self.respond(challenge[1 if parts[2]=="background.png" else 2],content_type="image/png")
        self.respond({"error":"NOT_FOUND"},404)

    def do_POST(self):
        if urlsplit(self.path).path != "/verify":
            return self.respond({"error":"NOT_FOUND"},404)
        try:
            size = int(self.headers.get("Content-Length","0"))
            if not 0 < size < 2048:
                raise ValueError
            payload = json.loads(self.rfile.read(size))
            offset = float(payload["offset"])
            with self.server.guard:
                expected = self.server.challenges.get(payload["id"])
            accepted = bool(expected and math.isfinite(offset) and abs(offset-expected[0]) <= 2)
            self.respond({"accepted":accepted})
        except (ValueError,KeyError,TypeError):
            self.respond({"error":"REQUEST_INVALID"},400)


def serve(host="0.0.0.0",port=18765):
    server = DemoServer((host,port))
    print(f"Demo listening on {host}:{server.server_port}. Open http://127.0.0.1:{server.server_port}",flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
