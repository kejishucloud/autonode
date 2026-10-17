# AutoNode — 自动化节点部署与统一订阅管理

[![AutoNode CI](https://github.com/kejishucloud/autonode/actions/workflows/ci.yml/badge.svg)](https://github.com/kejishucloud/autonode/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![License](https://img.shields.io/badge/License-MIT-green)

**AutoNode** 是基于 **sing-box、VLESS + REALITY** 的自动化节点部署与订阅管理项目。自动识别 VPS 系统和 CPU 架构，一键安装与配置服务，为每位用户生成**一个统一订阅地址**及二维码；同一用户可在多个设备与兼容客户端中复用该订阅。

## 核心功能

| 功能 | 说明 |
| --- | --- |
| 自动识别服务器环境 | 检查 Linux 系统和 CPU 架构（Ubuntu / Debian，amd64 / arm64） |
| 一键部署 | 安装 sing-box、生成 REALITY 密钥、写入配置并启动 systemd 服务 |
| 用户订阅 | **一用户、一组独立凭证、一个 URL**；多台设备共用，无需逐设备创建 |
| 多客户端适配 | 同一 URL 按请求的 `User-Agent` / `Accept` 自动返回 Mihomo YAML、Base64 VLESS 或 sing-box JSON |
| 用户管理 | 添加用户、查看订阅、列出用户、撤销用户及其所有设备的访问凭证 |
| 二维码 | 为用户生成订阅二维码与标准 VLESS 节点二维码 |
| 域名可选 | 域名 + Caddy HTTPS 订阅；没有域名时可以使用公网 IP 订阅 |
| 配置安全 | 验证配置、限制凭证文件权限，更新失败尽可能回滚 |
| 智能分流 | Mihomo / sing-box 订阅内置国内网站和 IP 直连、局域网直连、海外服务优先代理 |
| 规则集更新 | Mihomo MRS / sing-box SRS 每 24 小时更新，DNS 国内优先、海外回退经代理 |

### 客户端兼容性

| 客户端 | 常见平台 | 自动响应配置 |
| --- | --- | --- |
| Clash Verge Rev / Mihomo | Windows / macOS / Linux | Mihomo YAML |
| v2rayN / v2rayNG | Windows / Android | Base64 VLESS |
| Shadowrocket | iOS | Base64 VLESS |
| sing-box 1.14+ | 多平台 | 带 SRS 智能分流的 sing-box JSON（GUI 是否支持远程 JSON 取决于软件） |

**重要的客户端能力边界：** Mihomo 与 sing-box 格式包含分流规则；v2rayN/v2rayNG/Shadowrocket 取得的是 Base64 VLESS 节点，需要在各客户端独立配置分流策略。规则下载间隔为 24 小时，但首次下载和更新均要求代理节点可用。

所有用户使用同一条节点协议 **VLESS + REALITY（Vision）**，客户端必须具备相应协议支持。自动识别依赖客户端发送的请求头；部分软件或旧版本需要手动配置订阅 `User-Agent`，或扫描标准 VLESS 节点二维码导入。

## 项目架构

```text
                     AutoNode（Linux VPS）
                              │
                  sing-box / VLESS + REALITY
                              │
                  用户 A           用户 B
                  UUID A           UUID B
                  Token A          Token B
                    │                 │
          同一个订阅 URL A     同一个订阅 URL B
                    │
       ┌────────────┼────────────┐
    Clash/Mihomo   v2rayN     Shadowrocket
      Windows       Windows       iOS
                    │
           服务端自动协商格式
```

每位用户只有一个订阅 URL。示例（仅用于说明）：

```text
https://vpn.example.com/sub/<USER_TOKEN>
```

该 URL 可以在多个兼容设备上使用。**撤销某个用户后，其订阅令牌及 VLESS 身份会一同失效，不影响其他用户。**

## 运行要求

- Ubuntu / Debian VPS，`x86_64` 或 `aarch64`，具有 root / sudo 权限及公网 IPv4。
- 至少 512MB 内存，建议 1GB；可访问软件官方发行渠道。
- 能在 VPS 云安全组及主机防火墙配置入站 TCP 端口。
- 可选：已解析到 VPS 的域名，用于 HTTPS 订阅服务。

## 快速开始

### 1. 获取源码

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/kejishucloud/autonode.git
cd autonode
```

### 2. 一键安装

**有域名（推荐）：** 先将 `vpn.example.com` 的 A 记录指向你的 VPS，再执行：

```bash
sudo bash install.sh --domain vpn.example.com
```

默认节点端口为 TCP/8443，HTTPS 订阅服务为 TCP/443，证书申请使用 TCP/80。请检查云安全组和主机防火墙。

**无域名（IP 订阅）：**

```bash
sudo bash install.sh --allow-http
```

默认节点端口为 TCP/443，IP 订阅服务为 TCP/18080。若公网 IP 检测失败，可以指定：

```bash
sudo bash install.sh --host 203.0.113.10 --allow-http
```

`203.0.113.10` 是文档专用示例地址，实际部署必须替换。IP 订阅默认使用未加密的 HTTP，请注意**订阅 URL 包含访问令牌，传输中可能泄露**；长期使用建议配置 HTTPS 域名。节点连接的 REALITY 加密与订阅传输的 HTTPS 是两个独立环节。

### 3. 查看订阅与二维码

```bash
sudo autonode show-user default
```

输出类似：

```text
[AutoNode] 用户: default
统一订阅地址: https://vpn.example.com/sub/<USER_TOKEN>
节点 URI: vless://<USER_UUID>@vpn.example.com:8443?...
订阅二维码: /root/autonode-output/default-subscription.png
节点二维码: /root/autonode-output/default-node.png
```

`/root/autonode-output` 保存的二维码及配置包含用户访问凭证，应妥善保管。

### 4. 将同一个订阅添加到多台设备

在 Clash Verge Rev、v2rayN、Shadowrocket 等客户端的“订阅”或“远程配置”页面中，粘贴**同一个用户订阅 URL** 并更新即可。服务端基于请求头返回对应格式。若客户端无法识别响应，请先确认 VLESS + REALITY 协议支持情况及该软件的订阅请求头设置。

## 用户管理

```bash
# 为新用户创建独立订阅凭证（每用户一个订阅 URL）
sudo autonode add-user alice

# 查看该用户唯一订阅及二维码
sudo autonode show-user alice

# 查看用户状态，不打印凭证
sudo autonode list-users

# 撤销该用户在全部设备上的访问权限
sudo autonode revoke-user alice
```

用户名由字母、数字、下划线或连字符组成，最多 32 字符。

## 智能分流与国内订阅优化

新版 Mihomo 订阅自动生成 `kejishu-PROXY`、国内 MRS 规则集及 fake-ip/DNS 分流；新版 sing-box 1.14+ 客户端 JSON 采用 SRS 与独立 HTTP 下载链路。局域网优先直连、常见海外服务优先代理、国内域名/IP 直连，最后全部走代理。

**新用户直接使用原有统一订阅链接即可，无须手动贴脚本。** 旧版及第三方 Clash Verge 配置可使用 [扩展脚本](clients/clash-verge/override.js) 补充规则，但不要对新配置重复叠加。若大陆网络无法访问 Cloudflare Workers 订阅 URL，必须先解决订阅域名自身的可达性，客户端规则无法解决首次下载问题。

具体改造方案、DNS 解析顺序、规则源、兼容性边界、存量升级与验收方法参见 [智能分流与订阅优化指南](docs/SMART_ROUTING.md)。

## 运维与诊断

```bash
sudo systemctl status sing-box autonode-sub --no-pager
sudo journalctl -u sing-box -n 100 --no-pager
sudo journalctl -u autonode-sub -n 100 --no-pager
sudo sing-box check -c /etc/sing-box/config.json
sudo ss -lntp | grep -E ':(80|443|8443|18080)\b'
sudo curl -fsS http://127.0.0.1:18080/healthz
```

安装器会管理 `/etc/sing-box/config.json`。在已有 sing-box 服务的机器上安装前请备份配置，并预先检查端口冲突。具体步骤、故障排查与卸载方式见 [完整部署指南](docs/DEPLOYMENT.md)。

## 本地测试

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q autonode
bash -n install.sh uninstall.sh
node --check clients/clash-verge/override.js
node tests/test_override.js
```

## 项目结构

```text
autonode/
├── autonode/
│   ├── cli.py              # 部署、用户管理与二维码生成
│   ├── core.py             # 用户模型与订阅配置生成
│   └── server.py           # 一个 URL 的多客户端内容协商
├── autonode/routing.py    # 智能路由、DNS 与规则提供者
├── clients/clash-verge/override.js # 旧版 Clash Verge 扩展脚本
├── docs/DEPLOYMENT.md     # 从零部署及运维指南
├── docs/SMART_ROUTING.md   # 智能分流/可达性完整优化方案
├── tests/test_core.py     # 订阅、用户生命周期测试
├── tests/test_routing.py  # 智能分流路由契约测试
├── tests/test_override.js # 扩展脚本行为测试
├── install.sh             # Linux 一键安装器
├── uninstall.sh           # 卸载入口
└── .github/workflows/ci.yml
```

## 法律与免责声明

请在合法、获得授权的场景下部署和使用本项目。提供网络连接服务可能涉及所在地及服务对象所在地的许可、备案、网络安全和数据保护义务。**开源许可与免责声明不等于对具体运营行为的合法性保证，也无法免除依法不得排除的责任。**

详情参阅 [法律声明与风险提示（DISCLAIMER.md）](DISCLAIMER.md)。计划向第三方提供服务或开展收费业务前，建议先进行当地法律合规审查。

## License

本项目采用 [MIT License](LICENSE)。