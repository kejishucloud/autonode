# AutoNode 从零部署指南（统一用户订阅）

## 0. 准备

> **合规提示：** 部署前请核实服务器所在地、使用者所在地及实际服务场景所适用的法律法规和服务商条款；向其他人提供服务（尤其公开运营或收费）前，确认是否需要相关许可、备案及隐私保护措施。详见 [法律声明与风险提示](../DISCLAIMER.md)。免责条款不能代替合规审查。

- 一台合法拥有管理权限、支持公网 IPv4 的 Ubuntu / Debian VPS；记下其公网 IP、SSH 登录方式。
- 可以通过云控制台修改安全组。推荐域名以实现 HTTPS；不买域名也能创建节点，但是 IP 模式的订阅是 HTTP 明文。
- 确认服务器能使用 HTTPS 下载系统软件包、sing-box 官方安装脚本；需有 root 或 sudo 权限。
- 服务端只支持 Linux，macOS、Windows、iOS、Android 作为接收订阅的客户端，不应在客户端电脑执行安装脚本。

## 1. 登录 VPS

```bash
ssh root@YOUR_PUBLIC_IP
cat /etc/os-release
uname -m
ip -4 addr
sudo ss -lntp
```

安装脚本会识别 Ubuntu/Debian 与 `x86_64`/`aarch64`，不支持的平台会拒绝执行，不会删除现有服务。确认 TCP/443（IP 模式）或 TCP/8443（域名模式）未被其他服务占用。

## 2. 下载并运行

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/kejishucloud/autonode.git
cd autonode
```

无域名（HTTP 订阅）：

```bash
sudo bash install.sh --allow-http
```

有域名（建议，先配置 DNS A 记录）：

```bash
sudo bash install.sh --domain vpn.example.com
```

首次安装自动下载依赖，生成 REALITY 密钥、Short ID，写入配置，调用 `sing-box check`，启用 `sing-box` 和 `autonode-sub` systemd 服务，并输出一个默认用户的订阅和二维码。有域名时，安装 Caddy 并配置反向代理。已有 sing-box 配置时应先备份，因为首次安装会写入 `/etc/sing-box/config.json`。

## 3. 云安全组及防火墙

| 模式 | 必要公网端口 | 作用 |
|---|---|---|
| 仅 IP | TCP/443 | REALITY 节点 |
| 仅 IP | TCP/18080 | HTTP 订阅，存在凭证泄露风险 |
| 有域名 | TCP/8443 | REALITY 节点 |
| 有域名 | TCP/443 | HTTPS 订阅 |
| 有域名 | TCP/80 | Caddy 自动签发和更新证书 |

开放端口只针对你自己的 VPS。不要覆盖、关闭 SSH 端口和现有防火墙规则。需在云供应商安全组和 VPS 主机防火墙两个位置核对。域名使用 CDN 时，不要把标准 CDN HTTP 代理当作原始 REALITY TCP 转发。

## 4. 一个用户一个订阅链接

```bash
sudo autonode show-user default
```

示例：

```text
统一订阅地址: https://vpn.example.com/sub/<USER_TOKEN>
订阅二维码: /root/autonode-output/default-subscription.png
节点二维码: /root/autonode-output/default-node.png
```

在 Windows 的 v2rayN、macOS 的 Clash Verge Rev、iOS 的 Shadowrocket 等软件中，分别使用**同一个 URL** 作为远程订阅。它不是每台设备单独的 URL；不同客户端得到不同内容，凭证仍属于同一用户。请求 `User-Agent` 或 `Accept` 没有标明客户端类型时，默认 Base64 VLESS 格式。

客户端发送的 UA 不可控，无法保证任意版本软件自动识别格式。对于不能识别的客户端，先检查软件核心是否支持 VLESS + REALITY；必要时设置订阅 UA 或改用输出的 VLESS 节点二维码。原生 sing-box JSON 并非所有 GUI 都支持直接远程导入。

## 5. 创建和撤销用户

```bash
sudo autonode add-user alice
sudo autonode show-user alice
sudo autonode list-users
sudo autonode revoke-user alice
```

一个用户可在任意多台兼容设备使用同一节点和订阅。撤销用户时会同时禁用其 VLESS UUID 和订阅 Token；不得把某台设备误当成用户账户。需要分别控制家庭成员或同事时，为每个人分配独立用户，而不是为其每台电脑建立用户。

## 6. 查看故障

```bash
sudo systemctl status sing-box autonode-sub caddy --no-pager
sudo journalctl -u sing-box -n 100 --no-pager
sudo journalctl -u autonode-sub -n 100 --no-pager
sudo sing-box check -c /etc/sing-box/config.json
sudo ss -lntp | grep -E ':(80|443|8443|18080)\b'
sudo curl -fsS http://127.0.0.1:18080/healthz
```

常见问题：

1. **安装无法下载程序**：确认 DNS、HTTPS 出站和 VPS 所在地网络可达性；不要把不受信任的下载镜像脚本直接作为 root 执行。
2. **连接超时**：先检查云安全组、主机防火墙和端口冲突，再检查公网 IP、ISP 与网络路由。
3. **域名无法 HTTPS**：检查 DNS A 是否指向 VPS，TCP 80/443 是否可达，检查 Caddy 日志。
4. **同一订阅在 Clash 失败但 v2rayN 成功**：检查 Clash 是否用 Mihomo 核心及其 `User-Agent`，必要时设置 UA 为 `Mihomo`；旧 Clash 不支持 REALITY。
5. **Shadowrocket 订阅无法解析**：先升级客户端；可通过单节点二维码导入；不保证所有旧版本协议兼容。
6. **订阅返回 404**：核对 Token、用户是否已撤销；不要在公开 issue 或日志中展示 Token。
7. **订阅 IP 模式风险**：HTTP 无加密，可被中间人读出节点身份。推荐启用 HTTPS；节点的 REALITY 加密不等于订阅地址加密。

## 7. 卸载

```bash
sudo bash uninstall.sh --confirm
```

先备份你需要保留的配置（含凭证），再执行。卸载主要移除 AutoNode 生成的服务和文件，不卸载系统里的 sing-box/Caddy 软件包、不代替云安全组清理或 DNS 管理。