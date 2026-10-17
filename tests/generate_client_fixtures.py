"""为真实 Mihomo 和 sing-box 二进制生成不含真实节点凭据的配置。
用途：CI 和本地运行核心级 check；不会启动 VPN 或连接用户 VPS。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from autonode.core import mihomo_config, singbox_config, server_config
from tests.test_routing import sample_state


def main() -> None:
    """在输出目录写入两个客户端配置，并严格保持凭据仅为测试用例。"""
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m tests.generate_client_fixtures OUTPUT_DIR")
    folder = Path(sys.argv[1])
    folder.mkdir(parents=True, exist_ok=True)
    state = sample_state()
    (folder / "mihomo.yaml").write_text(mihomo_config(state, "demo"), encoding="utf-8")
    (folder / "singbox.json").write_text(
        json.dumps(singbox_config(state, "demo"), indent=2) + "\n", encoding="utf-8"
    )
    (folder / "singbox-server.json").write_text(
        json.dumps(server_config(state), indent=2) + "\n", encoding="utf-8"
    )
    print("generated: Mihomo, sing-box client and sing-box server fixtures")


if __name__ == "__main__":
    main()
