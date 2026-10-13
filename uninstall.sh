#!/usr/bin/env bash
set -Eeuo pipefail
if [[ $EUID -ne 0 ]]; then echo 'Please run with sudo' >&2; exit 1; fi
if [[ ${1:-} != --confirm ]]; then
  echo '将停用节点、删除全部用户凭证、配置与本地二维码。不会卸载 sing-box/caddy 软件包，不修改 Caddy 其他站点或防火墙。'
  echo '确认执行: sudo bash uninstall.sh --confirm'; exit 1
fi
systemctl disable --now autonode-sub.service 2>/dev/null || true
systemctl disable --now sing-box.service 2>/dev/null || true
rm -f /etc/systemd/system/autonode-sub.service /usr/local/bin/autonode
rm -rf /etc/autonode /root/autonode-output /opt/autonode
# 仅删除 AutoNode 专属 sing-box 配置，不删除发行版软件包。
rm -f /etc/sing-box/config.json
# 只清理自己的 Caddy 片段，不碰现有站点。
if [[ -f /etc/caddy/Caddyfile ]]; then
  python3 - <<'PYCODE'
from pathlib import Path
import re
p = Path('/etc/caddy/Caddyfile')
s = p.read_text()
clean = re.sub(r'\n?# BEGIN AUTONODE MANAGED BLOCK\n.*?# END AUTONODE MANAGED BLOCK\n', '\n', s, flags=re.S)
if clean != s:
    p.write_text(clean)
PYCODE
  systemctl reload caddy 2>/dev/null || true
fi
systemctl daemon-reload
echo 'AutoNode 卸载完成。Caddy 配置和云安全组/防火墙规则请按需手动检查。'