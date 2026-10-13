"""单 URL 多客户端格式协商的订阅 HTTP 服务。"""
from __future__ import annotations

import argparse
import hmac
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .core import base64_subscription, mihomo_config, singbox_config

LOG = logging.getLogger(__name__)


def choose_format(user_agent: str, accept: str = "") -> str:
    """按已知客户端 UA/Accept 猜测订阅格式，未知客户端回退 Base64。"""
    ua = user_agent.lower()
    media = accept.lower()
    if any(key in ua for key in ("clash", "mihomo", "stash", "clash-verge")):
        return "mihomo"
    if any(key in ua for key in ("sing-box", "sing_box")):
        return "singbox"
    # 避免浏览器请求的 text/html 或 */* 被误判成 Mihomo/JSON。
    if "application/vnd.sing-box+json" in media:
        return "singbox"
    if "application/x-yaml" in media or "application/vnd.mihomo+yaml" in media:
        return "mihomo"
    return "base64"


def render_request(state: dict, route: str, user_agent: str, accept: str = "") -> tuple[int, str, bytes]:
    """一个令牌对应一个用户，格式在服务端自动协商而不是拼接客户端专属 URL。"""
    if route == "/healthz":
        return 200, "text/plain; charset=utf-8", b"ok\n"
    parts = route.strip("/").split("/")
    if len(parts) != 2 or parts[0] != "sub":
        return 404, "text/plain; charset=utf-8", b"Not Found\n"
    token = parts[1]
    name = next((name for name, user in state["users"].items()
                 if user["enabled"] and hmac.compare_digest(user["token"], token)), None)
    if name is None:
        return 404, "text/plain; charset=utf-8", b"Not Found\n"
    fmt = choose_format(user_agent, accept)
    if fmt == "mihomo":
        return 200, "application/x-yaml; charset=utf-8", mihomo_config(state, name).encode()
    if fmt == "singbox":
        return 200, "application/json; charset=utf-8", (json.dumps(singbox_config(state, name), indent=2) + "\n").encode()
    return 200, "text/plain; charset=utf-8", (base64_subscription(state, name) + "\n").encode()


def make_handler(state_path: Path):
    """每次请求重载最新状态，新增/撤销用户立即生效。"""
    class Handler(BaseHTTPRequestHandler):
        server_version = "AutoNode/2.0"

        def do_GET(self) -> None:
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                code, ctype, body = render_request(
                    state, urlsplit(self.path).path,
                    self.headers.get("User-Agent", ""), self.headers.get("Accept", "")
                )
            except (OSError, ValueError, KeyError, TypeError):
                LOG.exception("Failed to serve subscription")
                code, ctype, body = 503, "text/plain; charset=utf-8", b"Service Unavailable\n"
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "private, no-store, max-age=0")
            self.send_header("Vary", "User-Agent, Accept")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            # BaseHTTPRequestHandler 默认打印完整请求 URL，包含 token，因此必须覆盖。
            LOG.info("request from %s status %s", self.client_address[0], args[1] if len(args) > 1 else "?")

    return Handler


def main() -> None:
    """作为受限 systemd 用户运行订阅服务。"""
    parser = argparse.ArgumentParser(description="AutoNode subscription server")
    parser.add_argument("--state", default="/etc/autonode/state.json")
    parser.add_argument("--listen", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    httpd = ThreadingHTTPServer((args.listen, args.port), make_handler(Path(args.state)))
    httpd.daemon_threads = True
    LOG.info("Subscription server listening on %s:%s", args.listen, args.port)
    httpd.serve_forever(poll_interval=0.5)


if __name__ == "__main__":
    main()