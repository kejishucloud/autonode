#!/usr/bin/env bash
# AutoNode Ubuntu/Debian 安装器；仅在 VPS 上以 root 执行。
set -Eeuo pipefail
trap 'echo "[ERROR] 安装失败，请检查上方日志。行: $LINENO" >&2' ERR

if [[ ${EUID} -ne 0 ]]; then echo "请使用 sudo bash install.sh [options]" >&2; exit 1; fi
if [[ $(uname -s) != Linux ]]; then
  echo "服务端仅支持 Linux VPS。Windows / macOS 为客户端，请导入生成的订阅。" >&2; exit 1
fi
source /etc/os-release
if [[ "${ID:-}" != ubuntu && "${ID:-}" != debian ]]; then
  echo "当前系统 ${ID:-unknown} 不支持自动安装（支持 Debian/Ubuntu）。" >&2; exit 1
fi
case "$(uname -m)" in
  x86_64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "架构不支持: $(uname -m)" >&2; exit 1 ;;
esac
printf '[INFO] system=%s version=%s arch=%s\n' "$ID" "${VERSION_ID:-unknown}" "$ARCH"
if [[ -f /etc/autonode/state.json ]]; then
  echo "[ERROR] 检测到已安装节点，拒绝覆盖。使用 sudo autonode show 查看。" >&2; exit 1
fi
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "$SCRIPT_DIR/autonode/cli.py" ]]; then
  echo "[ERROR] 请先下载完整仓库后，在仓库根目录执行 install.sh。" >&2; exit 1
fi
DOMAIN=''
ARGS=("$@")
for ((i=0; i<${#ARGS[@]}; i++)); do
  if [[ ${ARGS[i]} == --domain && $((i+1)) -lt ${#ARGS[@]} ]]; then DOMAIN=${ARGS[i+1]}; fi
  if [[ ${ARGS[i]} == --domain=* ]]; then DOMAIN=${ARGS[i]#*=}; fi
done
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl ca-certificates python3 qrencode
if [[ -n $DOMAIN ]]; then apt-get install -y -qq caddy; fi
if ! command -v sing-box >/dev/null 2>&1; then
  echo '[INFO] 正在运行 sing-box 官方安装程序 (https://sing-box.app/install.sh)'
  TMP_INSTALL=$(mktemp)
  trap 'rm -f "${TMP_INSTALL:-}"' EXIT
  curl --fail --location --silent --show-error --retry 3 --proto '=https' --tlsv1.2 \
    https://sing-box.app/install.sh -o "$TMP_INSTALL"
  bash "$TMP_INSTALL"
  rm -f "$TMP_INSTALL"
fi
sing-box version | head -n 1
id -u autonode >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin autonode
install -d -m 755 /opt/autonode
cp -R "$SCRIPT_DIR/autonode" /opt/autonode/
find /opt/autonode/autonode -type d -exec chmod 755 {} +
find /opt/autonode/autonode -type f -exec chmod 644 {} +
cat > /usr/local/bin/autonode <<'EOF'
#!/bin/sh
cd /opt/autonode || exit 1
exec /usr/bin/python3 -m autonode.cli "$@"
EOF
chmod 755 /usr/local/bin/autonode
# 对现有 ufw 只添加规则，不重置策略或 SSH 访问。
NODE_PORT=443
SUB_PORT=18080
for ((i=0; i<${#ARGS[@]}; i++)); do
  if [[ ${ARGS[i]} == --port && $((i+1)) -lt ${#ARGS[@]} ]]; then NODE_PORT=${ARGS[i+1]}; fi
  if [[ ${ARGS[i]} == --port=* ]]; then NODE_PORT=${ARGS[i]#*=}; fi
  if [[ ${ARGS[i]} == --sub-port && $((i+1)) -lt ${#ARGS[@]} ]]; then SUB_PORT=${ARGS[i+1]}; fi
  if [[ ${ARGS[i]} == --sub-port=* ]]; then SUB_PORT=${ARGS[i]#*=}; fi
done
if [[ -n $DOMAIN && $NODE_PORT == 443 ]]; then NODE_PORT=8443; fi
# 先完成配置验证与服务启动，成功后再开放端口。
autonode install "${ARGS[@]}"
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q '^Status: active'; then
  ufw allow "${NODE_PORT}/tcp" comment 'AutoNode VLESS' || true
  if [[ -n $DOMAIN ]]; then
    ufw allow 80/tcp comment 'AutoNode ACME' || true
    ufw allow 443/tcp comment 'AutoNode HTTPS subscription' || true
  else
    ufw allow "${SUB_PORT}/tcp" comment 'AutoNode HTTP subscription' || true
  fi
fi
cat <<'EOF'

[下一步] 检查云厂商安全组（主机防火墙并不等于云安全组）：
  无域名: 开放 VLESS 节点 TCP/443（若自定义则按 --port）及 HTTP 订阅 TCP/18080。
  有域名: 开放 VLESS TCP/8443（或自定义端口）、ACME TCP/80、HTTPS TCP/443。
  云安全组必须单独配置；订阅令牌与二维码不要公开到 GitHub 或聊天群。
EOF