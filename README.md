# AutoNode — 一键部署 VPN 节点与多客户端订阅

[![AutoNode CI](https://github.com/kejishucloud/autonode/actions/workflows/ci.yml/badge.svg)](https://github.com/kejishucloud/autonode/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![License](https://img.shields.io/badge/License-MIT-green)

**面向个人自有 Linux VPS 的自动化 VLESS + REALITY 部署工具。** 自动识别服务器系统与架构、生成设备凭证、安装 sing-box、创建 systemd 服务、生成节点二维码与多个客户端专属订阅链接。**不是 VPN 服务提供商，不赠送服务器，也不支持内网穿透。**

> ⚠️ 软件兼容性提示：Clash 需支持 Mihomo/Clash Meta 的 REALITY，旧版 Clash Premium 不兼容。v2rayN 需新版 Xray 核心；Shadowrocket 需支持 VLESS+REALITY 的版本。不同客户端升级可能改变配置兼容性，建议使用当前正式版。

## 功能

| 功能 | 实现方式 |
| --- | --- |
| 自动识别服务端环境 | Ubuntu / Debian、amd64 / arm64；不支持 Windows/macOS 作为公网服务端 |
| 安装节点 | 官方 sing-box 安装程序 + VLESS REALITY Vision |
| 无域名节点 | 公网 IPv4 + HTTP IP 订阅，显式要求 `--allow-http` |
| 有域名节点 | 域名 + Caddy 自动 HTTPS 订阅，节点默认 TCP/8443 |
| Clash Verge Rev / Mihomo | `/clash.yaml` |
| v2rayN / v2rayNG | `/v2ray`，Base64 VLESS |
| Shadowrocket | `/shadowrocket`，Base64 VLESS；或扫描节点二维码 |
| sing-box | `/singbox.json`，完整本地混合入口 JSON |
| 标准节点链接 | `/raw`，单条 VLESS URI |
| 独立设备管理 | `add-device` 与 `revoke-device`，独立 UUID / token |
| 故障恢复 | 验证配置后重启；变更失败恢复上次配置 |

## 1. 前置条件

- 一台 **拥有公网 IPv4** 的 Ubuntu 22.04+/Debian 12+ VPS（也可在其他版本尝试，未全面验证）。SSH root/sudo 权限、开放安全组的能力、可访问 GitHub 和 sing-box 官方下载站。
- 至少 512MB 内存（推荐 1GB）；TCP 443（无域名），或 TCP 8443 + 80/443（有域名），以及无域名模式的 TCP 18080；如端口已占用，可用 `--port` 调整。
- 域名可选。如果使用，先设置 DNS A 记录解析至 VPS 公网 IP，且 **不要开启会代理普通 HTTP 的 CDN 橙云** 来转发原始 VLESS TCP 流量；普通代理并不等于任意 TCP 隧道。
- 操作请遵守当地法律法规与 VPS 供应商服务条款。不要把配置、二维码、订阅链接、密钥上传公开仓库。

## 2. 快速部署：仅 IP（无域名）

```bash
sudo apt-get update && sudo apt-get install -y git
# 克隆正式公开仓库
git clone https://github.com/kejishucloud/autonode.git
cd autonode
# 显式同意 HTTP 订阅明文风险
sudo bash install.sh --allow-http
```

安装器自动检测公网 IPv4。如果服务器在特殊 NAT 环境或自动检测失败，明确指定公网地址：

```bash
sudo bash install.sh --host 203.0.113.10 --allow-http
```

> `203.0.113.10` 是文档示例保留 IP，必须替换为你自己真实的公网 IPv4。**IP 订阅使用未加密的 HTTP**；任何获得订阅地址或抓取 HTTP 流量的一方可能取得设备节点凭证。个人设备更推荐通过 SSH 安全地复制一次 VLESS 节点 URI，而不是长期使用 HTTP 自动更新。节点流量本身由 REALITY 加密，与订阅 HTTP 不同。

## 3. 域名部署：HTTPS 订阅（推荐）

先到 DNS 提供商添加：`vpn.example.com -> VPS 公网 IPv4`，等 DNS 生效后：

```bash
sudo bash install.sh --domain vpn.example.com
```

默认端口：VLESS REALITY TCP `8443`，Caddy HTTPS 订阅 TCP `443`，ACME 证书签发 TCP `80`。Caddy 会追加 AutoNode 专用配置片段到 `/etc/caddy/Caddyfile`，保留现有内容，但如果已有复杂同域名规则或占用冲突，Caddy 校验可能失败，需要自行调整。证书签发需要域名正确指向 VPS，入站 80/443 可达。

如果 DNS 尚未生效，请先等待。脚本不会自动配置云安全组、DNS 账号或购买 VPS。

## 4. 安装后输出示例

运行：

```bash
sudo autonode show
```

程序打印（这里仅为结构示例，**不是可使用节点**）：

```text
节点 URI: vless://<DEVICE_UUID>@<PUBLIC_IPV4>:443?encryption=none&security=reality&...#AutoNode-default
clash        http://<PUBLIC_IPV4>:18080/sub/<TOKEN>/clash.yaml
v2rayn       http://<PUBLIC_IPV4>:18080/sub/<TOKEN>/v2ray
shadowrocket http://<PUBLIC_IPV4>:18080/sub/<TOKEN>/shadowrocket
singbox      http://<PUBLIC_IPV4>:18080/sub/<TOKEN>/singbox.json
raw          http://<PUBLIC_IPV4>:18080/sub/<TOKEN>/raw
```

域名模式会输出 `https://vpn.example.com/sub/...`。本地保存 `/root/autonode-output/default.txt` 和 `/root/autonode-output/default.png`（二维码）；文件权限受限，请不要截图公开分享。二维码承载单个节点 URI，而非全部订阅 URL。

## 5. 导入不同客户端

1. **Clash Verge Rev / Mihomo**：配置 → 新建/导入远程配置 → 粘贴 `clash` URL → 更新/启用配置。旧版 Clash 核心不支持 REALITY。
2. **v2rayN（Windows）**：订阅分组 → 添加订阅 → 填入 `v2rayn` URL → 更新订阅；也可将 `raw` URL 返回的 VLESS URI 粘贴至导入框。
3. **Shadowrocket（iOS）**：添加订阅类型的 URL 使用 `shadowrocket` 链接；或扫描本地 PNG 产生的二维码导入单节点。部分版本可能需要直接使用单节点 URI。
4. **sing-box**：获取 `singbox` URL 返回的 JSON 文件，作为客户端配置加载；它包含本地 `127.0.0.1:2080` 混合入口。**不是所有 sing-box GUI 都接受 URL 订阅**，不支持时请手动下载导入 JSON。

`/sub/<TOKEN>` 会根据 User-Agent 尝试自动识别格式，但**推荐始终使用客户端专属 URL**。

## 6. 多设备与撤销

默认 `default` 是一个设备身份，可以同时被多个终端使用。若需要独立撤销权限，应每台设备建立独立凭证：

```bash
sudo autonode add-device iphone
sudo autonode add-device windows
sudo autonode add-device macbook
sudo autonode list-devices
sudo autonode show iphone
sudo autonode revoke-device iphone
```

每台设备有独立 UUID + 随机 256-bit 级 Token；撤销会更新服务端用户列表，旧订阅立即返回 404。**这是凭证隔离，而不是设备硬件绑定；持有相同 UUID 的多台设备仍可同时使用。**

## 7. 管理、诊断与卸载

```bash
sudo systemctl status sing-box autonode-sub --no-pager
sudo journalctl -u sing-box -n 100 --no-pager
sudo journalctl -u autonode-sub -n 100 --no-pager
sudo sing-box check -c /etc/sing-box/config.json
sudo ss -lntp | grep -E ':(443|8443|18080)\b'
sudo curl -fsS http://127.0.0.1:18080/healthz
sudo bash uninstall.sh --confirm
```

安装器只为活动中的 UFW 添加所需规则，不更改 SSH 默认端口、不清空防火墙；仍须独立修改 VPS 云安全组。卸载不会删除 sing-box/caddy 软件包、其他站点配置与安全组规则。若安装后改动过 Caddyfile，请备份并检查 AutoNode 标记片段。

## 8. 安全说明与局限

- 只为你合法控制的 VPS 部署。公开下载的 shell 安装程序是供应链边界；正式生产使用建议审阅源码并固定官方发行版版本。
- 无域名 IP 模式必须手动确认 `--allow-http`；HTTP 订阅不加密且带 Token，不适合公开分享。推荐使用 HTTPS 域名。
- 服务端配置和完整状态位于 `/etc/sing-box/config.json` 与 `/etc/autonode/state.json`，后者 root 用户和 `autonode` 组可读；不要在日志中粘贴它们。
- 默认只创建一台 VPS 上的一个节点，不提供机场面板、付费用户管理、流量限制、多 VPS 聚合或内网穿透。
- 端口冲突、IP 封锁、DNS 错误、运营商限制和云安全组未放通不能靠订阅转换解决。
- 如果同一 VPS 上存在其他 sing-box 配置或多服务 Caddy 规则，**先备份**。安装器拒绝覆盖已有 AutoNode 状态文件，但首次安装会管理 `/etc/sing-box/config.json`；建议独立干净 VPS。

## 9. 测试与开发

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q autonode
bash -n install.sh uninstall.sh
```

项目仅依赖 Python 标准库；服务端依赖官方 sing-box 与可选的 Caddy、二维码命令 `qrencode`。GitHub Actions 在 Python 3.10/3.12 上执行静态检查和单测。

完整从零教程：[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

## License

MIT。项目是技术演示与自托管工具，请遵守当地法规与第三方客户端许可。