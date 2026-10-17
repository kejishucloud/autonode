"""跨客户端分流模板基本契约（无网络依赖）。"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from autonode.routing import OVERSEAS_DOMAINS


ROOT = Path(__file__).resolve().parents[1]


class ClientProfilesTest(unittest.TestCase):
    """保证生成器规则与手动导入的客户端配置没有关键方向冲突。"""

    def test_xray_json_strategy(self):
        data = json.loads((ROOT / "clients/v2rayn/routing.json").read_text(encoding="utf-8"))
        self.assertEqual(data["domainStrategy"], "IPIfNonMatch")
        rules = data["rules"]
        self.assertEqual(rules[0]["outboundTag"], "direct")
        self.assertEqual(rules[1]["outboundTag"], "direct")
        self.assertEqual(rules[2]["outboundTag"], "proxy")
        self.assertEqual(rules[-1]["ip"], ["geoip:cn"])
        self.assertEqual(rules[-1]["outboundTag"], "direct")
        for domain in OVERSEAS_DOMAINS:
            # 强制代理例外必须与 Mihomo/Xray 一致。
            self.assertIn("domain:" + domain, rules[2]["domain"])

    def test_shadowrocket_final_and_priority(self):
        text = (ROOT / "clients/shadowrocket/kejishu.conf").read_text(encoding="utf-8")
        rules = [
            line.strip() for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#") and "," in line
            and line.split(",", 1)[0] in ("DOMAIN-SUFFIX", "IP-CIDR", "GEOIP", "FINAL")
        ]
        self.assertEqual(rules[-1], "FINAL,PROXY")
        self.assertLess(rules.index("DOMAIN-SUFFIX,openai.com,PROXY"),
                        rules.index("DOMAIN-SUFFIX,cn,DIRECT"))
        self.assertLess(rules.index("GEOIP,CN,DIRECT"),
                        rules.index("FINAL,PROXY"))
        self.assertIn("IP-CIDR,192.168.0.0/16,DIRECT,no-resolve", rules)


if __name__ == "__main__":
    unittest.main()
