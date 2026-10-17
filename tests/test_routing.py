"""AutoNode 智能分流契约：不依赖 DNS、VPS、第三方包。"""
from __future__ import annotations

import json
import unittest

from autonode.core import mihomo_config, singbox_config
from autonode.routing import (
    DOMESTIC_DOMAINS, MRS_BASE, OVERSEAS_DOMAINS,
    PROXY_GROUP, mihomo_rule_providers, mihomo_rules, singbox_route,
)


def sample_state() -> dict:
    """构造与真实用户凭据无关的测试节点。"""
    return {
        "version": 2, "host": "203.0.113.10", "domain": "",
        "node_port": 443, "sub_port": 18080, "sni": "www.microsoft.com",
        "private_key": "a" * 43, "public_key": "b" * 43,
        "short_id": "abcdef1234567890",
        "users": {
            "demo": {"uuid": "b1f3870c-d4f8-45f0-9489-6f0f477da534",
                     "token": "sampletoken" * 4, "enabled": True},
        },
    }


class RoutingContractTest(unittest.TestCase):
    """验证生成结果可被客户端引用，并确保规则执行顺序符合预期。"""

    def test_group_and_final(self):
        rules = mihomo_rules()
        self.assertEqual(rules[-1], f"MATCH,{PROXY_GROUP}")
        self.assertEqual(rules.count(rules[-1]), 1)
        self.assertLess(rules.index("RULE-SET,kejishu_cn_domain,DIRECT"),
                        rules.index("RULE-SET,kejishu_cn_ip,DIRECT"))
        self.assertNotIn("RULE-SET,kejishu_cn_ip,DIRECT,no-resolve", rules)

    def test_priority(self):
        rules = mihomo_rules()
        self.assertLess(rules.index("DOMAIN-SUFFIX,local,DIRECT"),
                        rules.index(f"DOMAIN-SUFFIX,github.com,{PROXY_GROUP}"))
        self.assertLess(rules.index(f"DOMAIN-SUFFIX,googleapis.cn,{PROXY_GROUP}"),
                        rules.index("DOMAIN-SUFFIX,cn,DIRECT"))
        self.assertLess(rules.index("DOMAIN-SUFFIX,taobao.com,DIRECT"),
                        rules.index("RULE-SET,kejishu_cn_domain,DIRECT"))
        for domain in OVERSEAS_DOMAINS:
            self.assertIn(f"DOMAIN-SUFFIX,{domain},{PROXY_GROUP}", rules)
        for domain in DOMESTIC_DOMAINS:
            self.assertIn(f"DOMAIN-SUFFIX,{domain},DIRECT", rules)

    def test_private_ipv4_ipv6(self):
        rules = mihomo_rules()
        for network in ("192.168.0.0/16", "10.0.0.0/8", "fc00::/7", "fe80::/10"):
            self.assertIn(f"IP-CIDR,{network},DIRECT,no-resolve", rules)

    def test_mrs_providers(self):
        providers = mihomo_rule_providers()
        self.assertEqual(set(providers), {"kejishu_cn_domain", "kejishu_cn_ip"})
        self.assertEqual(providers["kejishu_cn_domain"]["behavior"], "domain")
        self.assertEqual(providers["kejishu_cn_ip"]["behavior"], "ipcidr")
        for provider in providers.values():
            self.assertEqual(provider["interval"], 86400)
            self.assertEqual(provider["format"], "mrs")
            self.assertEqual(provider["proxy"], PROXY_GROUP)
            self.assertTrue(provider["url"].startswith(MRS_BASE))

    def test_generated_mihomo_includes_every_rule(self):
        yaml = mihomo_config(sample_state(), "demo")
        self.assertIn(f'  - name: "{PROXY_GROUP}"', yaml)
        self.assertIn("  enable: true", yaml)
        self.assertIn("enhanced-mode: fake-ip", yaml)
        self.assertIn("rule-providers:", yaml)
        self.assertIn('    format: "mrs"', yaml)
        self.assertIn("interval: 86400", yaml)
        self.assertIn("rules:", yaml)
        for rule in mihomo_rules():
            self.assertIn(json.dumps(rule), yaml)
        self.assertEqual(yaml.count(json.dumps(f"MATCH,{PROXY_GROUP}")), 1)
        self.assertEqual(yaml.count("rules:"), 1)

    def test_singbox_route_uses_srs_not_mrs(self):
        route = singbox_route()
        self.assertEqual(route["final"], "AutoNode")
        self.assertEqual(len(route["rule_set"]), 2)
        for item in route["rule_set"]:
            self.assertTrue(item["url"].endswith(".srs"))
            self.assertEqual(item["format"], "binary")
            self.assertEqual(item["download_detour"], "AutoNode")
            self.assertEqual(item["update_interval"], "1d")
        self.assertEqual(route["rules"][0]["outbound"], "direct")
        self.assertEqual(route["rules"][2]["outbound"], "AutoNode")

    def test_singbox_config_contains_cache_and_route(self):
        config = singbox_config(sample_state(), "demo")
        self.assertEqual(config["route"], singbox_route())
        self.assertTrue(config["experimental"]["cache_file"]["enabled"])
        self.assertEqual({outbound["tag"] for outbound in config["outbounds"]},
                         {"AutoNode", "direct"})


if __name__ == "__main__":
    unittest.main()
