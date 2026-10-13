"""VPS 初始化、用户生命周期与统一订阅二维码的命令行接口。"""
from __future__ import annotations

import argparse
import copy
import ipaddress
import json
import os
import re
import shutil
import grp
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from .core import (new_user, node_uri, server_config, subscription_url,
                   valid_host, valid_name, valid_port, validate_state)

STATE = Path("/etc/autonode/state.json")
SINGBOX = Path("/etc/sing-box/config.json")
PUBLIC_STATE = Path("/etc/autonode/subscriptions.json")
OUTPUT = Path("/root/autonode-output")
KEY_RE = re.compile(r"(?im)^\s*(privatekey|publickey|private_key|public_key)\s*:\s*([A-Za-z0-9_-]{43})\s*$")


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """通过参数数组执行命令，拒绝 shell 拼接与注入。"""
    return subprocess.run(args, check=check, capture_output=True, text=True)


def require_root() -> None:
    """校验 root 权限；安装文件与私钥必须归 root。"""
    if os.geteuid() != 0:
        raise RuntimeError("请使用 sudo 或 root 运行")


def save_private(path: Path, content: str, mode: int = 0o600) -> None:
    """同目录原子替换文件，保证私钥文件没有短暂的宽松权限。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".autonode-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def protect_state_file() -> None:
    """私钥文件仅允许 root 读取；订阅快照只对订阅服务组开放。"""
    gid = grp.getgrnam("autonode").gr_gid
    os.chown(STATE, 0, 0)
    os.chmod(STATE, 0o600)
    os.chown(PUBLIC_STATE, 0, gid)
    os.chmod(PUBLIC_STATE, 0o640)


def load_state() -> dict:
    """读取并验证持久化状态文件。"""
    state = json.loads(STATE.read_text(encoding="utf-8"))
    validate_state(state)
    return state


def detect_public_ipv4() -> str:
    """从公共 IP 回显服务检测 VPS 公网 IPv4，不信任内网地址。"""
    for url in ("https://api.ipify.org", "https://ipv4.icanhazip.com"):
        try:
            request = Request(url, headers={"User-Agent": "autonode/1.0"})
            with urlopen(request, timeout=6) as response:
                ip = response.read(64).decode().strip()
            parsed = ipaddress.IPv4Address(ip)
            if parsed.is_global:
                return str(parsed)
        except (OSError, ValueError):
            continue
    raise RuntimeError("无法发现公网 IPv4，请指定 --host YOUR_PUBLIC_IP")


def reality_keypair() -> tuple[str, str]:
    """调用 sing-box 生成 REALITY X25519 密钥对，不通过远程第三方生成。"""
    result = run("sing-box", "generate", "reality-keypair")
    keys = {key.replace("_", "").lower(): value for key, value in KEY_RE.findall(result.stdout)}
    if not keys.get("privatekey") or not keys.get("publickey"):
        raise RuntimeError("sing-box 未返回有效 REALITY 密钥对")
    return keys["privatekey"], keys["publickey"]


def write_systemd(domain: str, sub_port: int) -> None:
    """生成独立的订阅服务单元，域名模式仅监听本机环回。"""
    listen = "127.0.0.1" if domain else "0.0.0.0"
    content = f"""[Unit]
Description=AutoNode multi-client subscription service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=autonode
Group=autonode
WorkingDirectory=/opt/autonode
ExecStart=/usr/bin/python3 -m autonode.server --state /etc/autonode/subscriptions.json --listen {listen} --port {sub_port}
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadOnlyPaths=/etc/autonode/subscriptions.json
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
CapabilityBoundingSet=

[Install]
WantedBy=multi-user.target
"""
    save_private(Path("/etc/systemd/system/autonode-sub.service"), content, 0o644)


def update_singbox(new_state: dict, previous: dict | None = None) -> None:
    """验证配置后应用并重启，失败恢复原配置和上一次状态。"""
    config = json.dumps(server_config(new_state), ensure_ascii=False, indent=2) + "\n"
    SINGBOX.parent.mkdir(parents=True, exist_ok=True)
    old_config = SINGBOX.read_text(encoding="utf-8") if SINGBOX.exists() else None
    old_public = PUBLIC_STATE.read_text(encoding="utf-8") if PUBLIC_STATE.exists() else None
    save_private(SINGBOX, config)
    try:
        run("sing-box", "check", "-c", str(SINGBOX))
        save_private(STATE, json.dumps(new_state, indent=2) + "\n")
        public = {key: value for key, value in new_state.items() if key != "private_key"}
        save_private(PUBLIC_STATE, json.dumps(public, indent=2) + "\n")
        protect_state_file()
        # 让订阅服务读取最新状态，同时重新加载 VLESS 用户。
        run("systemctl", "restart", "sing-box")
        run("systemctl", "is-active", "--quiet", "sing-box")
    except (subprocess.CalledProcessError, OSError):
        if old_config is not None:
            save_private(SINGBOX, old_config)
        else:
            SINGBOX.unlink(missing_ok=True)
        if previous is not None:
            save_private(STATE, json.dumps(previous, indent=2) + "\n")
            public_prev = {key: value for key, value in previous.items() if key != "private_key"}
            save_private(PUBLIC_STATE, json.dumps(public_prev, indent=2) + "\n")
            protect_state_file()
        else:
            STATE.unlink(missing_ok=True)
            if old_public is None:
                PUBLIC_STATE.unlink(missing_ok=True)
            else:
                save_private(PUBLIC_STATE, old_public)
                os.chown(PUBLIC_STATE, 0, grp.getgrnam("autonode").gr_gid)
                os.chmod(PUBLIC_STATE, 0o640)
        if old_config is not None:
            run("systemctl", "restart", "sing-box", check=False)
        raise


def show_user(state: dict, name: str, qr: bool = True) -> None:
    """每名用户只显示一个订阅地址，生成订阅二维码和直连节点二维码。"""
    url = subscription_url(state, name)
    uri = node_uri(state, name)
    print(f"\n[AutoNode] 用户: {name}")
    print(f"统一订阅地址: {url}")
    print(f"节点 URI: {uri}")
    OUTPUT.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(OUTPUT, 0o700)
    save_private(OUTPUT / f"{name}.txt", f"用户: {name}\n统一订阅: {url}\n节点: {uri}\n")
    if qr and shutil.which("qrencode"):
        subscription_png = OUTPUT / f"{name}-subscription.png"
        node_png = OUTPUT / f"{name}-node.png"
        run("qrencode", "-o", str(subscription_png), "-s", "7", url)
        run("qrencode", "-o", str(node_png), "-s", "7", uri)
        os.chmod(subscription_png, 0o600)
        os.chmod(node_png, 0o600)
        print(f"订阅二维码: {subscription_png}")
        print(f"节点二维码: {node_png}")
    if not state.get("domain"):
        print("[警告] IP 订阅通过明文 HTTP 提供，token 和 UUID 可能被截获；优先配置 HTTPS。")
    print("[提示] 多台设备复用同一用户订阅，格式通过客户端 User-Agent 自动识别。")


def install(args: argparse.Namespace) -> None:
    """部署全新节点；如已有状态则阻止覆盖。"""
    require_root()
    if STATE.exists():
        raise RuntimeError("节点已部署。请使用 show-user/add-user/revoke-user，避免误覆盖密钥。")
    domain = valid_host(args.domain) if args.domain else ""
    if domain:
        try:
            ipaddress.ip_address(domain)
        except ValueError:
            pass
        else:
            raise ValueError("--domain 必须是域名，IP 请使用 --host")
    if not domain and not args.allow_http:
        raise RuntimeError("IP 订阅为 HTTP 明文，请明确传入 --allow-http 确认接受风险")
    host = valid_host(args.host) if args.host else (domain or detect_public_ipv4())
    sni = valid_host(args.sni)
    node_port = valid_port(args.port or (8443 if domain else 443))
    sub_port = valid_port(args.sub_port)
    if domain and (node_port in (80, 443) or sub_port in (80, 443)):
        raise ValueError("域名订阅预留 TCP 80/443 给 Caddy，请将节点/订阅服务放在其他端口")
    if node_port == sub_port:
        raise ValueError("节点端口与订阅端口不能相同")
    if domain and not shutil.which("caddy"):
        raise RuntimeError("域名模式必须先安装 caddy")
    try:
        addr = ipaddress.ip_address(host)
        if addr.version != 4:
            raise ValueError("当前版本暂只支持公网 IPv4 节点，请指定 --host IPv4")
    except ValueError as exc:
        if '暂只支持' in str(exc):
            raise
    private, public = reality_keypair()
    state = {"version": 2, "host": host, "domain": domain,
             "node_port": node_port, "sub_port": sub_port,
             "sni": sni, "private_key": private, "public_key": public,
             "short_id": os.urandom(8).hex(), "users": {"default": new_user()}}
    validate_state(state)
    write_systemd(domain, sub_port)
    update_singbox(state)
    run("systemctl", "daemon-reload")
    try:
        run("systemctl", "enable", "--now", "autonode-sub.service")
        run("systemctl", "is-active", "--quiet", "autonode-sub.service")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("订阅服务启动失败：请运行 journalctl -u autonode-sub -n 100") from exc
    if domain:
        caddy = Path("/etc/caddy/Caddyfile")
        if not shutil.which("caddy"):
            raise RuntimeError("域名模式需要先安装 Caddy；节点已安装，可按 README 配置反向代理。")
        marker = "# BEGIN AUTONODE MANAGED BLOCK"
        original = caddy.read_text(encoding="utf-8") if caddy.exists() else ""
        if marker in original:
            raise RuntimeError("Caddyfile 已有 AutoNode 配置，请勿重复部署")
        addition = (f"\n{marker}\n{domain} {{\n"
                    f"    reverse_proxy 127.0.0.1:{sub_port}\n}}\n"
                    "# END AUTONODE MANAGED BLOCK\n")
        save_private(caddy, original.rstrip() + "\n" + addition, 0o644)
        try:
            run("caddy", "validate", "--config", str(caddy))
            run("systemctl", "enable", "--now", "caddy")
            run("systemctl", "reload", "caddy")
        except subprocess.CalledProcessError:
            save_private(caddy, original, 0o644)
            raise
    print("[OK] sing-box 与订阅服务已安装；请同时放通云安全组和主机防火墙。")
    show_user(state, "default")


def modify_user(name: str, enabled: bool) -> None:
    """新增用户或撤销用户；一名用户可同时连接任意数量的兼容设备。"""
    require_root()
    valid_name(name)
    original = load_state()
    updated = copy.deepcopy(original)
    if enabled:
        if name in updated["users"]:
            raise ValueError("用户名称已存在；请换一个用户名")
        updated["users"][name] = new_user()
    else:
        if name not in updated["users"] or not updated["users"][name]["enabled"]:
            raise ValueError("用户不存在或已经撤销")
        updated["users"][name]["enabled"] = False
    update_singbox(updated, original)
    if enabled:
        show_user(updated, name)
    else:
        print(f"已撤销用户 {name}：此用户的订阅令牌和 VLESS UUID 对所有设备失效。")


def main() -> None:
    """AutoNode CLI：一用户一订阅；用户不需要为不同设备建立不同链接。"""
    parser = argparse.ArgumentParser(prog="autonode", description="AutoNode VPS 部署与统一订阅管理")
    sub = parser.add_subparsers(dest="command", required=True)
    inst = sub.add_parser("install", help="首次部署 VPS 节点与默认用户")
    inst.add_argument("--domain", help="HTTPS 订阅域名，DNS A 必须解析到本 VPS")
    inst.add_argument("--host", help="节点公网 IPv4 或域名；缺省自动检测")
    inst.add_argument("--sni", default="www.microsoft.com", help="REALITY 握手用 SNI")
    inst.add_argument("--port", type=int, help="节点端口；有域名默认 8443，否则默认 443")
    inst.add_argument("--sub-port", type=int, default=18080, help="订阅 HTTP 内网监听端口")
    inst.add_argument("--allow-http", action="store_true", help="明确确认无域名的 HTTP 明文订阅风险")
    show = sub.add_parser("show-user", help="输出某位用户的单一订阅 URL 与二维码")
    show.add_argument("name", nargs="?", default="default")
    sub.add_parser("show", help="显示默认用户订阅（show-user default 别名）")
    add = sub.add_parser("add-user", help="创建独立用户凭证与订阅 URL")
    add.add_argument("name")
    revoke = sub.add_parser("revoke-user", help="撤销该用户在所有设备上的节点访问权限")
    revoke.add_argument("name")
    sub.add_parser("list-users", help="列出用户名及状态，不输出令牌")
    args = parser.parse_args()
    try:
        if args.command == "install":
            install(args)
        elif args.command in ("show", "show-user"):
            require_root()
            state = load_state()
            show_user(state, valid_name(getattr(args, "name", "default")))
        elif args.command == "add-user":
            modify_user(args.name, True)
        elif args.command == "revoke-user":
            modify_user(args.name, False)
        elif args.command == "list-users":
            require_root()
            for name, info in load_state()["users"].items():
                print(f"{name}: {'active' if info['enabled'] else 'revoked'}")
    except (ValueError, KeyError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()