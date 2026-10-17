/**
 * AutoNode / kejishu - Clash Verge Rev (Mihomo) 全局扩展脚本
 * 安装位置：订阅配置 -> 扩展脚本；只有需要给旧订阅补充规则时使用。
 * AutoNode 新版订阅已内置规则，请不要再次叠加脚本。
 *
 * @param {Object} config 订阅解析后的配置对象
 * @returns {Object} 生成的 Mihomo 配置
 */
function main(config) {
  if (!config || typeof config !== "object") {
    throw new Error("AutoNode: 无效订阅配置");
  }

  const PROXY = "kejishu-PROXY";
  const groups = Array.isArray(config["proxy-groups"]) ? config["proxy-groups"] : [];
  const proxies = Array.isArray(config.proxies) ? config.proxies : [];

  // 兼容老版 AutoNode 只有 AutoNode 组、没有 kejishu-PROXY 的情况。
  if (!groups.some(group => group.name === PROXY)) {
    const candidates = groups
      .filter(group => group && typeof group.name === "string" && group.name !== PROXY)
      .map(group => group.name);
    const nodes = proxies
      .filter(node => node && typeof node.name === "string")
      .map(node => node.name);
    const targets = nodes.length ? nodes : candidates;
    if (!targets.length) {
      throw new Error("AutoNode: 订阅未提供可用的代理节点或代理组");
    }
    config["proxy-groups"] = [
      ...groups,
      { name: PROXY, type: "select", proxies: [...new Set([...targets, "DIRECT"])] }
    ];
  }

  const base = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/";
  config["rule-providers"] = {
    ...(config["rule-providers"] || {}),
    kejishu_cn_domain: {
      type: "http", behavior: "domain", format: "mrs",
      url: base + "geosite/cn.mrs",
      path: "./ruleset/kejishu_cn_domain.mrs",
      interval: 86400, proxy: PROXY
    },
    kejishu_cn_ip: {
      type: "http", behavior: "ipcidr", format: "mrs",
      url: base + "geoip/cn.mrs",
      path: "./ruleset/kejishu_cn_ip.mrs",
      interval: 86400, proxy: PROXY
    }
  };

  const privateDomains = ["local", "localhost", "lan", "home.arpa"];
  const privateIps = [
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12",
    "192.168.0.0/16", "169.254.0.0/16", "100.64.0.0/10",
    "::1/128", "fc00::/7", "fe80::/10"
  ];
  const foreignDomains = [
    "openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com",
    "anthropic.com", "claude.ai", "github.com", "githubusercontent.com",
    "githubassets.com", "google.com", "googleapis.com", "googleapis.cn",
    "gstatic.com", "youtube.com", "youtu.be", "ytimg.com",
    "googlevideo.com", "telegram.org", "t.me", "x.com", "twitter.com",
    "discord.com"
  ];
  const domesticDomains = [
    "cn", "baidu.com", "qq.com", "weixin.qq.com", "taobao.com",
    "tmall.com", "jd.com", "alipay.com", "bilibili.com", "douyin.com",
    "zhihu.com", "163.com", "126.com", "douban.com"
  ];

  const privateRules = [
    ...privateDomains.map(domain => `DOMAIN-SUFFIX,${domain},DIRECT`),
    ...privateIps.map(cidr => `IP-CIDR,${cidr},DIRECT,no-resolve`)
  ];
  const overseasRules = foreignDomains.map(domain => `DOMAIN-SUFFIX,${domain},${PROXY}`);
  const domesticRules = domesticDomains.map(domain => `DOMAIN-SUFFIX,${domain},DIRECT`);
  const oldRules = (Array.isArray(config.rules) ? config.rules : []).filter(rule =>
    typeof rule === "string" &&
    !/^\s*MATCH\s*,/i.test(rule) &&
    !/^\s*RULE-SET\s*,kejishu_cn_(domain|ip)\s*,/i.test(rule)
  );

  config.rules = [...new Set([
    ...privateRules,
    ...overseasRules,
    ...oldRules,
    ...domesticRules,
    "RULE-SET,kejishu_cn_domain,DIRECT",
    // 不加 no-resolve，允许解析未知国内域名以匹配国内 IP。
    "RULE-SET,kejishu_cn_ip,DIRECT",
    `MATCH,${PROXY}`
  ])];

  const smartDns = {
    enable: true,
    ipv6: false,
    "enhanced-mode": "fake-ip",
    "fake-ip-filter": ["+.lan", "+.local", "+.home.arpa", "localhost"],
    "default-nameserver": ["223.5.5.5", "119.29.29.29"],
    "proxy-server-nameserver": ["223.5.5.5", "119.29.29.29"],
    nameserver: ["https://dns.alidns.com/dns-query", "https://doh.pub/dns-query"],
    "nameserver-policy": {
      "rule-set:kejishu_cn_domain": [
        "https://dns.alidns.com/dns-query", "https://doh.pub/dns-query"
      ],
      "+.lan": "system",
      "+.local": "system",
      "+.home.arpa": "system"
    },
    fallback: [
      `https://1.1.1.1/dns-query#${PROXY}`,
      `https://8.8.8.8/dns-query#${PROXY}`
    ],
    "fallback-filter": { geoip: true, "geoip-code": "CN" }
  };

  const currentDns = config.dns && typeof config.dns === "object" ? config.dns : {};
  config.dns = {
    ...smartDns,
    ...currentDns,
    "nameserver-policy": {
      ...smartDns["nameserver-policy"],
      ...(currentDns["nameserver-policy"] || {})
    }
  };
  config.mode = "rule";
  return config;
}
