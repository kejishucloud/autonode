#!/usr/bin/env bash
# AutoNode 无损升级：仅替换订阅 Python 模块，不重建节点与用户凭据。
set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "[ERROR] 请使用 sudo bash upgrade.sh" >&2
  exit 1
fi

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP="/opt/autonode"
OLD="$APP/autonode"
STATE="/etc/autonode/subscriptions.json"
if [[ ! -f "$ROOT/autonode/core.py" || ! -f "$ROOT/tests/test_core.py" ]]; then
  echo "[ERROR] 必须在完整的 AutoNode Git 仓库中执行。" >&2
  exit 1
fi
if [[ ! -d "$OLD" || ! -r "$STATE" ]] || ! systemctl cat autonode-sub.service >/dev/null 2>&1; then
  echo "[ERROR] 未检测到已安装的 AutoNode 订阅服务；首次部署请使用 install.sh。" >&2
  exit 1
fi
if ! command -v python3 >/dev/null || ! command -v systemctl >/dev/null; then
  echo "[ERROR] 缺少 python3/systemctl。" >&2
  exit 1
fi

# 启动前先执行全部离线测试，不对现有服务做任何更改。
(
  cd "$ROOT"
  python3 -m unittest discover -s tests -v
  python3 -m compileall -q autonode tests
)
STAGING="$(mktemp -d "$APP/.autonode-stage.XXXXXXXX")"
BACKUP="/var/backups/autonode/$(date -u +%Y%m%dT%H%M%SZ)-$$"
PREVIOUS="$APP/.autonode-previous-$$"
RESTORE_REQUIRED=false

cleanup() {
  rm -rf -- "$STAGING"
}
restore() {
  local exit_status=$?
  trap - ERR
  if [[ "$RESTORE_REQUIRED" == true && -d "$PREVIOUS" ]]; then
    echo "[WARN] 升级失败，正在恢复原代码并重启订阅服务。" >&2
    rm -rf -- "$OLD"
    mv -- "$PREVIOUS" "$OLD"
    systemctl restart autonode-sub.service || true
  fi
  cleanup
  exit "$exit_status"
}
trap cleanup EXIT
trap restore ERR

install -d -m 0700 "$BACKUP"
cp -a -- "$OLD" "$BACKUP/module"
cp -a -- /etc/autonode "$BACKUP/state"
cp -a -- "$ROOT/autonode" "$STAGING/autonode"
find "$STAGING/autonode" -type d -exec chmod 0755 {} +
find "$STAGING/autonode" -type f -exec chmod 0644 {} +
python3 -m compileall -q "$STAGING/autonode"

# 使用已安装的公开订阅快照生成配置；不打印 UUID、token 或密钥。
PYTHONPATH="$STAGING" AUTONODE_PUBLIC_STATE="$STATE" python3 - <<'PY'
import json
import os
from pathlib import Path
from autonode.core import mihomo_config, singbox_config, validate_state

state = json.loads(Path(os.environ["AUTONODE_PUBLIC_STATE"]).read_text(encoding="utf-8"))
# 公开订阅状态不含服务端私钥，为校验模型添加不落盘的占位符。
state["private_key"] = "a" * 43
validate_state(state)
users = [name for name, user in state["users"].items() if user["enabled"]]
if not users:
    raise SystemExit("无启用用户，拒绝升级")
name = users[0]
mihomo = mihomo_config(state, name)
sing = singbox_config(state, name)
assert "MATCH,kejishu-PROXY" in mihomo
assert "RULE-SET,kejishu_cn_domain,DIRECT" in mihomo
assert sing["route"]["final"] == "AutoNode"
print("[OK] 订阅生成校验成功（不打印任何凭据）")
PY

PORT="$(python3 -c 'import json; print(json.load(open("/etc/autonode/subscriptions.json"))["sub_port"])')"
echo "[INFO] 备份目录：$BACKUP"
mv -- "$OLD" "$PREVIOUS"
RESTORE_REQUIRED=true
mv -- "$STAGING/autonode" "$OLD"
systemctl restart autonode-sub.service

healthy=false
for i in 1 2 3 4 5; do
  if curl --silent --fail --max-time 3 "http://127.0.0.1:${PORT}/healthz" | grep -qx 'ok'; then
    healthy=true
    break
  fi
  sleep 1
done
if [[ "$healthy" != true ]]; then
  echo "[ERROR] 升级后服务健康检查失败" >&2
  false
fi

RESTORE_REQUIRED=false
rm -rf -- "$PREVIOUS"
echo "[OK] AutoNode 订阅模块已无损升级，用户 UUID/token/REALITY 节点保持不变。"
echo "[INFO] 备份保存在 $BACKUP（含敏感数据，禁止公开）。"
