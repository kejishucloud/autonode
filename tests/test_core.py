"""无需网络与 root 权限即可运行的单用户单订阅契约测试。"""
from __future__ import annotations

import base64
import copy
import json
import unittest

from autonode.core import (
    base64_subscription, mihomo_config, new_user, node_uri,
    server_config, singbox_config, subscription_url, valid_host,
    valid_name, validate_state,
)
from autonode.server import choose_format, render_request


class AutoNodeTest(unittest.TestCase):
    """测试用户凭证隔离、多端复用、内容协商与用户撤销。"""

    def setUp(self):
        self.state = {
            "version": 2, "host": "203.0.113.10", "domain": "",
            "node_port": 443, "sub_port": 18080, "sni": "www.microsoft.com",
            "private_key": "a" * 43, "public_key": "b" * 43,
            "short_id": "1a2b3c4d5e6f7788", "users": {
                "alice": {"uuid": "b1f3870c-d4f8-45f0-9489-6f0f477da534",
                          "token": "testtoken" * 5, "enabled": True},
                "bob": {"uuid": "7ce86a4a-29f9-4980-94d4-6b8e2812d58a",
                        "token": "anothertoken" * 4, "enabled": True},
            },
        }

    def test_server_config_multi_user(self):
        config = server_config(self.state)
        self.assertEqual(len(config["inbounds"][0]["users"]), 2)
        self.assertTrue(config["inbounds"][0]["tls"]["reality"]["enabled"])
        self.assertNotIn("public_key", config["inbounds"][0]["tls"]["reality"])

    def test_single_subscription_and_direct_uri(self):
        link = node_uri(self.state, "alice")
        self.assertTrue(link.startswith("vless://"))
        for key in ("pbk=", "sid=", "security=reality", "flow=xtls-rprx-vision"):
            self.assertIn(key, link)
        self.assertEqual(base64.b64decode(base64_subscription(self.state, "alice")).decode().strip(), link)
        self.assertEqual(subscription_url(self.state, "alice"), f"http://203.0.113.10:18080/sub/{self.state['users']['alice']['token']}")

    def test_mihomo(self):
        yaml = mihomo_config(self.state, "alice")
        self.assertIn("reality-opts:", yaml)
        self.assertIn("xtls-rprx-vision", yaml)
        self.assertIn('servername: "www.microsoft.com"', yaml)

    def test_singbox_client(self):
        config = singbox_config(self.state, "bob")
        self.assertEqual(config["outbounds"][0]["tls"]["reality"]["public_key"], "b" * 43)
        self.assertEqual(config["inbounds"][0]["listen"], "127.0.0.1")
        json.loads(json.dumps(config))

    def test_same_url_auto_formats(self):
        url = subscription_url(self.state, "alice")
        route = "/sub/" + url.rsplit("/", 1)[-1]
        for ua, accept, expected in (
            ("Clash-Verge/v2", "*/*", "reality-opts:"),
            ("Mihomo/1.0", "", "reality-opts:"),
            ("sing-box/1.13", "*/*", '"outbounds"'),
            ("v2rayN/7.0", "*/*", ""),
            ("Shadowrocket/2.2", "*/*", ""),
        ):
            status, _, payload = render_request(self.state, route, ua, accept)
            self.assertEqual(status, 200)
            if expected:
                self.assertIn(expected, payload.decode())
            else:
                self.assertIn("vless://", base64.b64decode(payload.strip()).decode())
        self.assertEqual(render_request(self.state, route + "/clash.yaml", "Clash")[0], 404)
        self.assertEqual(render_request(self.state, "/sub/invalid", "v2rayN")[0], 404)

    def test_negotiation_accept_and_fallback(self):
        self.assertEqual(choose_format("unknown", "application/vnd.sing-box+json"), "singbox")
        self.assertEqual(choose_format("unknown", "application/vnd.mihomo+yaml"), "mihomo")
        self.assertEqual(choose_format("Mozilla", "text/html,*/*"), "base64")

    def test_user_isolation(self):
        alice = self.state["users"]["alice"]["token"]
        bob = self.state["users"]["bob"]["token"]
        self.assertNotEqual(alice, bob)
        self.assertNotEqual(node_uri(self.state, "alice"), node_uri(self.state, "bob"))
        self.assertNotIn(self.state["users"]["bob"]["uuid"], render_request(self.state, f"/sub/{alice}", "Mihomo")[2].decode())

    def test_revoke_user(self):
        state = copy.deepcopy(self.state)
        state["users"]["alice"]["enabled"] = False
        token = state["users"]["alice"]["token"]
        self.assertEqual(render_request(state, f"/sub/{token}", "Clash")[0], 404)
        self.assertEqual(len(server_config(state)["inbounds"][0]["users"]), 1)

    def test_host_validation(self):
        self.assertEqual(valid_host("EXAMPLE.COM"), "example.com")
        self.assertEqual(valid_host("1.1.1.1"), "1.1.1.1")
        for bad in ("http://example.com", "localhost:443", "a/b", " bad.example", "foo\nbar"):
            with self.assertRaises(ValueError):
                valid_host(bad)
        with self.assertRaises(ValueError):
            valid_name("bad/name")

    def test_domain_https_url(self):
        state = copy.deepcopy(self.state)
        state["domain"] = state["host"] = "vpn.example.com"
        state["node_port"] = 8443
        self.assertTrue(subscription_url(state, "alice").startswith("https://vpn.example.com/sub/"))
        self.assertNotIn("/clash", subscription_url(state, "alice"))

    def test_new_user_uniqueness(self):
        self.assertNotEqual(new_user()["token"], new_user()["token"])
        self.assertNotEqual(new_user()["uuid"], new_user()["uuid"])

    def test_duplicate_token_rejected(self):
        state = copy.deepcopy(self.state)
        state["users"]["bob"]["token"] = state["users"]["alice"]["token"]
        with self.assertRaises(ValueError):
            validate_state(state)


if __name__ == "__main__":
    unittest.main()