"""AutoNode 数据模型、配置验证和多客户端配置生成模块（仅 Python 标准库）。"""
from __future__ import annotations

import base64
import ipaddress
import json
import re
import secrets
import uuid
from urllib.parse import quote


_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,31}$")
_HOST = re.compile(r"^(?=.{1,253}$)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$")
_KEY = re.compile(r"^[A-Za-z0-9_-]{43}$")


def valid_host(value: str) -> str:
    """验证主机名或 IP，拒绝 URL、空白、端口、路径和控制字符。"""
    if not isinstance(value, str) or value != value.strip():
        raise ValueError("主机名不得为空或包含多余空白")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        if not _HOST.fullmatch(value):
            raise ValueError(f"非法主机名或 IP: {value!r}") from None
        return value.lower()


def valid_name(value: str) -> str:
    """检查用户标识，只允许安全的 ASCII 字母、数字、下划线和连字符。"""
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise ValueError("用户名称只能包含字母、数字、_、-，长度 1-32")
    return value


def valid_port(value: int) -> int:
    """验证端口范围。"""
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535:
        raise ValueError("端口范围必须为 1-65535")
    return value


def new_user() -> dict:
    """生成一名用户的 UUID、256-bit 随机订阅 token 和启用状态。"""
    return {"uuid": str(uuid.uuid4()), "token": secrets.token_urlsafe(32), "enabled": True}


def validate_state(state: dict) -> None:
    """对磁盘状态做基本校验，避免生成无效或注入型配置。"""
    valid_host(state["host"])
    valid_host(state["sni"])
    valid_port(state["node_port"])
    valid_port(state["sub_port"])
    if state["node_port"] == state["sub_port"]:
        raise ValueError("节点与订阅服务不能使用同一端口")
    if not _KEY.fullmatch(state["public_key"]) or not _KEY.fullmatch(state["private_key"]):
        raise ValueError("REALITY 公私钥格式错误")
    if not re.fullmatch(r"(?:[a-fA-F0-9]{2}){1,8}", state["short_id"]):
        raise ValueError("short_id 必须是 2-16 位十六进制字符")
    if state.get("domain"):
        domain = valid_host(state["domain"])
        try:
            ipaddress.ip_address(domain)
        except ValueError:
            pass
        else:
            raise ValueError("domain 必须是域名，不能是 IP")
    if state.get("version") != 2 or not isinstance(state.get("users"), dict):
        raise ValueError("当前仅支持 AutoNode v2 用户状态格式")
    token_set: set[str] = set()
    uuid_set: set[str] = set()
    for name, user in state["users"].items():
        valid_name(name)
        value = str(uuid.UUID(user["uuid"]))
        token = user["token"]
        if not isinstance(token, str) or len(token) < 32 or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
            raise ValueError("订阅 token 格式错误")
        if value in uuid_set or token in token_set:
            raise ValueError("用户 UUID 或 token 重复")
        uuid_set.add(value)
        token_set.add(token)
        if not isinstance(user["enabled"], bool):
            raise ValueError("enabled 必须为布尔值")


def user_state(state: dict, name: str) -> dict:
    """读取已启用用户的节点凭证；不存在或停用则拒绝。"""
    user = state["users"].get(name)
    if not user or not user["enabled"]:
        raise KeyError("用户不存在或已停用")
    return user


def server_config(state: dict) -> dict:
    """生成单 VPS、多用户认证的 sing-box VLESS/REALITY 服务端配置。"""
    validate_state(state)
    users = [
        {"name": name, "uuid": data["uuid"], "flow": "xtls-rprx-vision"}
        for name, data in state["users"].items() if data["enabled"]
    ]
    if not users:
        raise ValueError("至少需要一个启用用户")
    return {
        "log": {"level": "warn", "timestamp": True},
        "inbounds": [{
            "type": "vless", "tag": "autonode-vless", "listen": "0.0.0.0",
            "listen_port": state["node_port"], "users": users,
            "tls": {"enabled": True, "server_name": state["sni"],
                    "reality": {"enabled": True,
                                "handshake": {"server": state["sni"], "server_port": 443},
                                "private_key": state["private_key"],
                                "short_id": [state["short_id"]]}}
        }],
        "outbounds": [{"type": "direct", "tag": "direct"}],
    }


def node_uri(state: dict, name: str) -> str:
    """为指定用户生成同一节点的标准 VLESS 链接，跨兼容客户端复用。"""
    user = user_state(state, name)
    host = state["host"]
    host = f"[{host}]" if ":" in host else host
    query = ("encryption=none&security=reality&type=tcp&flow=xtls-rprx-vision"
             f"&sni={quote(state['sni'], safe='')}&fp=chrome"
             f"&pbk={state['public_key']}&sid={state['short_id']}")
    return f"vless://{user['uuid']}@{host}:{state['node_port']}?{query}#AutoNode-{quote(name, safe='')}"


def base64_subscription(state: dict, name: str) -> str:
    """面向 v2rayN、Shadowrocket 等客户端的 Base64 VLESS 订阅正文。"""
    return base64.b64encode((node_uri(state, name) + "\n").encode()).decode()


def mihomo_config(state: dict, name: str) -> str:
    """为 Clash Verge Rev/Mihomo 生成 YAML；JSON 引号同样是合法 YAML 字符串。"""
    user = user_state(state, name)
    label = f"AutoNode-{name}"
    q = lambda item: json.dumps(item, ensure_ascii=True)
    return "\n".join([
        "mixed-port: 7890", "allow-lan: false", "mode: rule", "log-level: warning",
        "proxies:", f"  - name: {q(label)}", "    type: vless",
        f"    server: {q(state['host'])}", f"    port: {state['node_port']}",
        f"    uuid: {q(user['uuid'])}", "    network: tcp", "    udp: true",
        "    tls: true", "    flow: xtls-rprx-vision", "    client-fingerprint: chrome",
        f"    servername: {q(state['sni'])}", "    reality-opts:",
        f"      public-key: {q(state['public_key'])}",
        f"      short-id: {q(state['short_id'])}",
        "proxy-groups:", "  - name: AutoNode", "    type: select", "    proxies:",
        f"      - {q(label)}", "      - DIRECT", "rules:", "  - MATCH,AutoNode", "",
    ])


def singbox_config(state: dict, name: str) -> dict:
    """为 sing-box 原生客户端提供 JSON（GUI 是否支持 URL 订阅取决于客户端）。"""
    user = user_state(state, name)
    return {
        "log": {"level": "warn"},
        "inbounds": [{"type": "mixed", "tag": "local", "listen": "127.0.0.1", "listen_port": 2080}],
        "outbounds": [{
            "type": "vless", "tag": "AutoNode", "server": state["host"],
            "server_port": state["node_port"], "uuid": user["uuid"],
            "flow": "xtls-rprx-vision", "tls": {
                "enabled": True, "server_name": state["sni"],
                "utls": {"enabled": True, "fingerprint": "chrome"},
                "reality": {"enabled": True, "public_key": state["public_key"],
                            "short_id": state["short_id"]}
            }
        }, {"type": "direct", "tag": "direct"}],
    }


def subscription_url(state: dict, name: str) -> str:
    """一个用户只生成一个订阅 URL；响应由服务端根据客户端请求自动选择。"""
    user = user_state(state, name)
    authority = state.get("domain") or state["host"]
    if ":" in authority:
        authority = f"[{authority}]"
    base = f"https://{authority}" if state.get("domain") else f"http://{authority}:{state['sub_port']}"
    return f"{base}/sub/{user['token']}"