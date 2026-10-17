# AutoNode 智能分流与订阅优化方案

> 适用版本：本仓库 `feat/smart-routing` 改造；默认遵循“一个用户，一个 URL，多客户端协商格式”的现有契约。

## 1. 目标与范围

- 中国大陆域名 / IP **DIRECT**，内网、NAS、局域网设备 **DIRECT**。
- 海外及 AI / 开发服务走 `kejishu-PROXY`；未命中流量默认代理。
- Mihomo 远程规则集（MRS）与 sing-box 原生规则集（SRS）每 24 小时尝试更新。
- DNS 由国内解析优先、境外回退经代理完成，尽量消除海外 DNS 直连超时。
- **节点传输服务和订阅分发服务分开设计**，不影响 VLESS + REALITY / 用户 UUID / 订阅 token。
- 保留兼容：Clash Verge Rev、Mihomo、v2rayN、v2rayNG、Shadowrocket、sing-box；不承诺每种客户端都能自动导入路由规则。

## 2. 路由判定顺序

| 优先级 | 规则 | 处理 | 原因 |
|---|---|---|---|
| P0 | `.local` / `.lan` / `home.arpa`；RFC1918、回环、链路本地、IPv6 ULA | DIRECT | 内网访问不需要跨境往返 |
| P1 | OpenAI、Claude、GitHub、Google、YouTube、Telegram 等明确海外服务 | kejishu-PROXY | 规避域名使用国内 CDN 或国内 IP 时被误直连 |
| P2 | `.cn` 和常见国内平台域名 | DIRECT | 即使第一次没有下载远程规则也能直连 |
| P3 | MetaCubeX `geosite/cn.mrs`（sing-box: `geosite-cn.srs`） | DIRECT | 匹配更多国内域名 |
| P4 | MetaCubeX `geoip/cn.mrs`（sing-box: `geoip-cn.srs`） | DIRECT | 未命中域名规则时利用 CN IP 判定 |
| P5 | MATCH / sing-box final | kejishu-PROXY | 默认海外代理 |

重要：`RULE-SET,kejishu_cn_ip,DIRECT` **不加 `no-resolve`**。加上后，对于尚未取得 IP 的域名请求，这条规则可能不触发解析，造成大量国内网站落到代理兜底。私有网段规则保留 `no-resolve`，避免每条 IP 规则额外触发 DNS。

Mihomo 为 DNS 配置 `fallback-filter.geoip: true`；若海外服务使用了国内 CDN，P1 依旧高于国内规则。但任何规则集都有误判可能，请在客户端连接日志和规则匹配面板检查实际命中情况。

## 3. 新增文件与代码责任

| 路径 | 职责 |
|---|---|
| `autonode/routing.py` | 同一套分流意图生成 Mihomo 规则、DNS 与 sing-box 路由 |
| `autonode/core.py` | 订阅时自动生成完整 Mihomo YAML、带路由的 sing-box JSON |
| `clients/clash-verge/override.js` | 为**旧版或第三方 Mihomo 订阅**提供扩展脚本 |
| `tests/test_routing.py` | 检查直连/代理顺序、下载周期、MRS 与 SRS 区别 |
| `tests/test_override.js` | 校验扩展脚本重复执行、旧分组兼容、兜底顺序 |

**新版 AutoNode 订阅已内置分流，无须重复使用扩展脚本。**

## 4. 新部署 / 现有部署升级

### 首次部署

按 [DEPLOYMENT.md](DEPLOYMENT.md) 执行 `install.sh`，无需为每台设备创建不同订阅。新订阅根据请求头自动输出配置。Clash Verge Rev 使用 **Mihomo 核心**，导入 AutoNode 用户订阅后选择规则（Rule）模式。

### 已部署旧版 AutoNode

`install.sh` 检测到 `/etc/autonode/state.json` 会拒绝覆盖。**不得重新运行安装器来升级代码，也不要删除现有状态文件。**下面仅替换 Python 程序并在本地验证，保留用户数据：

```bash
git pull --ff-only
sudo cp -a /opt/autonode "/opt/autonode.backup.$(date +%Y%m%d%H%M%S)"
sudo cp -a autonode/. /opt/autonode/autonode/
sudo python3 -m compileall -q /opt/autonode/autonode
sudo systemctl restart autonode-sub
sudo systemctl status autonode-sub --no-pager
```

上述指令应在代码已进入默认分支、并在仓库根目录时执行；如果通过 PR 尚未合并，请先检查对应分支和代码版本。不需要改 VPS 的 sing-box 入站节点或重建密钥。**执行升级前务必保留原 `/opt/autonode` 和 `/etc/autonode` 备份；当前升级仅更新订阅输出逻辑。**

重启订阅服务后，客户端手动更新订阅。服务端已部署成功，并不代表每个客户端都已重载新路由。

## 5. Clash Verge Rev：无脚本 / 脚本两种模式

**模式 A：直接使用新版 AutoNode 统一订阅（推荐）**

1. 添加现有 `https://sub.example.com/sub/<TOKEN>`（地址仅示例；不要发布真实令牌）。
2. 选择带 Mihomo 支持的配置类型；必要时将订阅请求 `User-Agent` 设为 `Mihomo`。
3. 更新订阅，确认代理组 `kejishu-PROXY` 存在。
4. 在设置中选择 Rule / 规则模式，启用 TUN（需要系统代理全局接管时）并检查 DNS。
5. 日志验证本地/国内为 DIRECT，海外为 `kejishu-PROXY`。

**模式 B：旧版或第三方订阅附加脚本**

将 [override.js](../clients/clash-verge/override.js) 内容粘贴到 Clash Verge Rev 的扩展脚本中，使其作用于对应订阅。此脚本会保留原有非兜底规则、去除旧 `MATCH`，若旧订阅缺少 `kejishu-PROXY` 则从已有节点/分组建立新分组。已有的非兜底规则放在国内远程规则之前，保证原有自定义策略仍可用。

只在确实需要兼容老订阅时启用该脚本；不要在新版内置规则的配置上重复叠加。

### 5.1 DNS 与实际分流的关系

- 国内 DoH：`dns.alidns.com`、`doh.pub`；节点域名解析使用 `223.5.5.5` / `119.29.29.29`。
- 境外备用 DoH：1.1.1.1 / 8.8.8.8，指定经 `kejishu-PROXY` 请求，避免直接连接被拦截或超时。
- 本地 `.lan` / `.local` / `home.arpa` 不走 fake-ip；若内网使用企业专属后缀，请自行加入 fake-ip-filter 和 DNS policy。
- 默认 `ipv6: false`，避免仅 IPv6 流量绕过 IPv4 策略；如需 IPv6 请确认代理与本地网络均支持，再单独测试开启。

注意：无法保证所有局域网单标签主机名都由公共 DNS 解析。发现 NAS/打印机无法通过主机名访问时，应优先使用本机路由器 DNS 或系统解析器，不要将内网域名发往公共 DoH。

## 6. sing-box 客户端

服务端对 `User-Agent: sing-box` 输出原生 JSON，路由文件格式为 **SRS**，而不是 Mihomo 的 MRS。

- `route.rule_set` 定义 CN 域名和 CN IP 规则集；`update_interval=1d`。
- `experimental.cache_file.enabled=true`，用于远程规则缓存，断网时尽可能复用本地缓存。
- `download_detour: AutoNode` 使规则集经已有节点下载，兼容采用此字段的 sing-box 版本。
- `download_detour` 已在 sing-box 1.14 标记弃用；未来 1.16 版本移除时需迁移至 `http_client`。**升级内核前使用 `sing-box check -c <client.json>` 预先验证，不能保证所有 sing-box 版本通用。**
- 是否支持通过远程 URL 导入完整 JSON，取决于具体 GUI；某些 GUI 只能导入节点 URI。

## 7. v2rayN / v2rayNG / Shadowrocket 的规则

Base64 VLESS 订阅只包含节点 URI、UUID、REALITY 参数。**它不能直接携带 Clash 的 YAML 或 sing-box 的路由策略。**用户仍用相同订阅链接接收节点，分流需要在客户端设置：

- v2rayN / v2rayNG：选择路由模式或创建自定义 routing 规则，域名集 `geosite:cn`、IP 集 `geoip:cn` 和 `geoip:private` DIRECT，海外服务指定代理出站，最终缺省出站走代理。不同版本的导入语法不同，不要把 Mihomo MRS 文件直接导入 Xray 路由。
- Shadowrocket：在 **配置 / 规则** 中将 LAN、国内域/IP 设为 DIRECT，国外服务和 FINAL 设为节点；使用客户端支持的规则订阅格式并独立更新。Shadowrocket 不会自动读取 Python 中生成的 Mihomo YAML。

这里的规则管理仅规定策略，不声称客户端已自动接管这些设置。此限制来自不同客户端的订阅格式差异。

## 8. Cloudflare 与“国内不挂代理无法更新订阅”

这是**订阅入口可达性**问题，与节点出站分流是两个独立问题。客户端还没有拿到订阅前，本地智能路由当然无法发挥作用。

推荐链路：

```text
客户端 ── HTTPS:443 ── sub.example.com ── Caddy ── localhost:18080（AutoNode）
客户端 ── VLESS/REALITY TCP:8443 ───────── VPS sing-box 入站
                               ↓
                     境外互联网（节点代理）
```

如果当前订阅使用 Cloudflare Workers 的 `workers.dev` 域名且部分大陆网络不可达，优先使用自己控制的订阅域名，配置 **Cloudflare DNS only（灰云）**，让客户端直达 VPS 上的 HTTPS Caddy，而不是继续依赖 Workers 的 URL。真正迁移前应核对证书签发、DNS 解析、443 端口以及运营商网络测试。DNS only 不等于 CDN 加速或隐藏源站 IP；原站暴露也需要防火墙、日志脱敏和限速。不要把含令牌的 HTTP 订阅公开给第三方。

Cloudflare 普通 CDN HTTP 代理**不能**透明加速原生 VLESS + REALITY TCP 流量；应分别评估节点到用户的运营商路由、丢包、抖动、晚高峰 RTT、出口容量。若使用 Cloudflare 特定 TCP 产品，要核实功能、费用与地区可达性；不能默认免费 CDN 就能加速。

## 9. 验收清单与命令

```bash
# 本地仓库：无第三方 Python 依赖
python3 -m unittest discover -s tests -v
python3 -m compileall -q autonode tests
node --check clients/clash-verge/override.js
node tests/test_override.js

# VPS：检查订阅服务健康度，不打印用户令牌
sudo systemctl status autonode-sub sing-box --no-pager
sudo curl -fsS http://127.0.0.1:18080/healthz

# 获取 Mihomo 订阅后在客户端测试（切勿把真实订阅 URL 贴到公开 CI）
mihomo -t -f /path/to/client.yaml

# sing-box 客户端配置验证；仅在客户端安装了对应版本时执行
sing-box check -c /path/to/client.json
```

| 测试目标 | 预期 |
|---|---|
| NAS / 网关 / 局域网 IP | DIRECT，正常连接 |
| 淘宝、京东、B站、百度、政务网站 | DIRECT，尽可能使用国内 DNS |
| OpenAI、Google、YouTube、GitHub、Claude | kejishu-PROXY |
| 未列出的境外域名 | MATCH -> kejishu-PROXY |
| 更新规则集 | 24h 自动检查，首次下载需节点可用 |
| 撤销用户 | 同一 token 返回 404；原 UUID 禁用 |
| v2rayN / Shadowrocket | 原 URL 仍可获取 Base64 节点，客户端规则另行配置 |

本改造仅包含单元测试和配置生成测试。真正的互联网可达性、客户端规则命中、VPS 线路加速效果，都需要在目标客户端网络环境验收。**不应将配置生成成功等同于国内测速成功或延迟得到改善。**

## 10. 后续演进

1. 将 sing-box 远程下载迁移到新版 `http_client`（按客户端版本兼容，而非服务端版本）。
2. 加入规则集镜像源的可用性探测及离线初始缓存，避免用户首次启动就需要连接 GitHub。
3. 可为每个订阅增加可选分流档位（默认智能、全局、直连）；但要维持单一用户 URL 契约，避免强制按客户端创建不同 token。
4. 扩展 E2E 测试：使用真实 Mihomo / sing-box 二进制校验 YAML/JSON，以及 TUN/DNS/IPv6 场景测试。
5. 订阅域名与节点域名分别监控可达率、DNS 时间、TLS 握手和下载响应延迟；保护 token 避免进入 HTTP access log、Cloudflare Analytics 或公共错误报告。
