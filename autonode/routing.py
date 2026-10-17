"""AutoNode 客户端智能分流规则。规则只作用于客户端，不改变 VPS 出站。"""
from __future__ import annotations

import json

PROXY_GROUP = "kejishu-PROXY"
MRS_BASE = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/"
SRS_GEOSITE = "https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/"
SRS_GEOIP = "https://raw.githubusercontent.com/SagerNet/sing-geoip/rule-set/"

# 优先代理：必须放在 CN 域名和 CN IP 规则之前，避免海外服务的国内 CDN 错配。
OVERSEAS_DOMAINS = (
    "openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com",
    "anthropic.com", "claude.ai", "github.com", "githubusercontent.com",
    "githubassets.com", "google.com", "googleapis.com", "googleapis.cn",
    "gstatic.com", "youtube.com", "youtu.be", "ytimg.com",
    "googlevideo.com", "telegram.org", "t.me", "x.com", "twitter.com",
    "discord.com",
)

# 离线基础规则：远程规则首次下载失败时，仍能让常见国内网站直接连接。
DOMESTIC_DOMAINS = (
    "cn", "baidu.com", "qq.com", "weixin.qq.com", "taobao.com",
    "tmall.com", "jd.com", "alipay.com", "bilibili.com", "douyin.com",
    "zhihu.com", "163.com", "126.com", "douban.com",
)

PRIVATE_DOMAIN_SUFFIXES = ("local", "localhost", "lan", "home.arpa")
PRIVATE_IP_CIDRS = (
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12",
    "192.168.0.0/16", "169.254.0.0/16", "100.64.0.0/10",
    "::1/128", "fc00::/7", "fe80::/10",
)


def mihomo_rule_providers() -> dict[str, dict]:
    """返回供 Mihomo/Clash Verge 使用的 MRS 规则集，刷新周期为 24 小时。"""
    return {
        "kejishu_cn_domain": {
            "type": "http", "behavior": "domain", "format": "mrs",
            "url": MRS_BASE + "geosite/cn.mrs",
            "path": "./ruleset/kejishu_cn_domain.mrs",
            "interval": 86400, "proxy": PROXY_GROUP,
        },
        "kejishu_cn_ip": {
            "type": "http", "behavior": "ipcidr", "format": "mrs",
            "url": MRS_BASE + "geoip/cn.mrs",
            "path": "./ruleset/kejishu_cn_ip.mrs",
            "interval": 86400, "proxy": PROXY_GROUP,
        },
    }


def mihomo_rules() -> list[str]:
    """按顺序处理：私有网络、海外例外、国内常见域、远程 CN 域/IP、海外兜底。"""
    rules = [f"DOMAIN-SUFFIX,{name},DIRECT" for name in PRIVATE_DOMAIN_SUFFIXES]
    rules += [f"IP-CIDR,{cidr},DIRECT,no-resolve" for cidr in PRIVATE_IP_CIDRS]
    rules += [f"DOMAIN-SUFFIX,{name},{PROXY_GROUP}" for name in OVERSEAS_DOMAINS]
    rules += [f"DOMAIN-SUFFIX,{name},DIRECT" for name in DOMESTIC_DOMAINS]
    rules += [
        "RULE-SET,kejishu_cn_domain,DIRECT",
        # 不使用 no-resolve：否则未命中域名规则的国内域名不会解析 IP 来匹配国内网段。
        "RULE-SET,kejishu_cn_ip,DIRECT",
        f"MATCH,{PROXY_GROUP}",
    ]
    return rules


def mihomo_dns_lines() -> list[str]:
    """本地和国内使用国内解析，海外回退经代理查询，避免海外 DNS 直连超时。"""
    return [
        "dns:",
        "  enable: true",
        "  ipv6: false",
        "  enhanced-mode: fake-ip",
        "  fake-ip-filter:",
        '    - "+.lan"',
        '    - "+.local"',
        '    - "+.home.arpa"',
        '    - "localhost"',
        "  default-nameserver:",
        "    - 223.5.5.5",
        "    - 119.29.29.29",
        "  proxy-server-nameserver:",
        "    - 223.5.5.5",
        "    - 119.29.29.29",
        "  nameserver:",
        "    - https://dns.alidns.com/dns-query",
        "    - https://doh.pub/dns-query",
        "  nameserver-policy:",
        "    'rule-set:kejishu_cn_domain':",
        "      - https://dns.alidns.com/dns-query",
        "      - https://doh.pub/dns-query",
        "    '+.lan': system",
        "    '+.local': system",
        "    '+.home.arpa': system",
        "  fallback:",
        f"    - https://1.1.1.1/dns-query#{PROXY_GROUP}",
        f"    - https://8.8.8.8/dns-query#{PROXY_GROUP}",
        "  fallback-filter:",
        "    geoip: true",
        "    geoip-code: CN",
    ]


def mihomo_provider_lines() -> list[str]:
    """输出简洁 YAML，不依赖 PyYAML；所有 URL 和路径都转义为 YAML 双引号字符串。"""
    lines = ["rule-providers:"]
    for name, provider in mihomo_rule_providers().items():
        lines.append(f"  {name}:")
        for key, value in provider.items():
            encoded = json.dumps(value) if isinstance(value, str) else str(value)
            lines.append(f"    {key}: {encoded}")
    return lines


def singbox_route() -> dict:
    """sing-box 原生 SRS 规则；MRS 和 SRS 不可互换。"""
    return {
        "rules": [
            {"ip_is_private": True, "outbound": "direct"},
            {"domain_suffix": list(PRIVATE_DOMAIN_SUFFIXES), "outbound": "direct"},
            {"domain_suffix": list(OVERSEAS_DOMAINS), "outbound": "AutoNode"},
            {"domain_suffix": list(DOMESTIC_DOMAINS), "outbound": "direct"},
            {"rule_set": "kejishu_cn_domain", "outbound": "direct"},
            {"rule_set": "kejishu_cn_ip", "outbound": "direct"},
        ],
        "rule_set": [
            {
                "tag": "kejishu_cn_domain", "type": "remote", "format": "binary",
                "url": SRS_GEOSITE + "geosite-cn.srs",
                "http_client": {"detour": "AutoNode"}, "update_interval": "1d",
            },
            {
                "tag": "kejishu_cn_ip", "type": "remote", "format": "binary",
                "url": SRS_GEOIP + "geoip-cn.srs",
                "http_client": {"detour": "AutoNode"}, "update_interval": "1d",
            },
        ],
        "final": "AutoNode",
    }
