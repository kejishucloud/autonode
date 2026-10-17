/* AutoNode extension script smoke tests (Node.js built-in modules only). */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../clients/clash-verge/override.js"), "utf8");
const context = vm.createContext({});
vm.runInContext(source, context, { filename: "override.js" });
assert.equal(typeof context.main, "function");

function copy(value) {
  return JSON.parse(JSON.stringify(value));
}
const config = {
  proxies: [{ name: "AutoNode-demo", type: "vless" }],
  "proxy-groups": [{ name: "AutoNode", type: "select", proxies: ["AutoNode-demo"] }],
  rules: ["DOMAIN-SUFFIX,custom.example,DIRECT", "MATCH,AutoNode"],
};
let updated = copy(context.main(copy(config)));
assert.equal(updated["proxy-groups"].filter(x => x.name === "kejishu-PROXY").length, 1);
assert.equal(updated.rules.filter(x => x.startsWith("MATCH,")).length, 1);
assert.equal(updated.rules.at(-1), "MATCH,kejishu-PROXY");
assert(updated.rules.indexOf("DOMAIN-SUFFIX,custom.example,DIRECT") > 0);
assert(updated.rules.indexOf("DOMAIN-SUFFIX,local,DIRECT") < updated.rules.indexOf("DOMAIN-SUFFIX,custom.example,DIRECT"));
assert(updated.rules.indexOf("DOMAIN-SUFFIX,github.com,kejishu-PROXY") < updated.rules.indexOf("DOMAIN-SUFFIX,cn,DIRECT"));
assert.equal(updated["rule-providers"].kejishu_cn_ip.interval, 86400);
assert.equal(updated["rule-providers"].kejishu_cn_ip.behavior, "ipcidr");
assert.equal(updated.dns["enhanced-mode"], "fake-ip");
assert(updated.rules.includes("IP-CIDR6,fc00::/7,DIRECT,no-resolve"));
assert(updated.rules.includes("IP-CIDR6,fe80::/10,DIRECT,no-resolve"));
assert(updated.dns.fallback.every(x => x.endsWith("#kejishu-PROXY")));

// 重复运行脚本不得创建重复分组 / MATCH / 规则。
updated = copy(context.main(updated));
assert.equal(updated["proxy-groups"].filter(x => x.name === "kejishu-PROXY").length, 1);
assert.equal(updated.rules.filter(x => x.startsWith("MATCH,")).length, 1);
assert.equal(updated.rules.filter(x => x === "RULE-SET,kejishu_cn_ip,DIRECT").length, 1);

// 原订阅已经包含代理组时不得覆盖节点选择。
const modern = {
  proxies: [{ name: "node" }],
  "proxy-groups": [{ name: "kejishu-PROXY", type: "select", proxies: ["node", "DIRECT"] }],
  rules: ["MATCH,kejishu-PROXY"],
};
assert.equal(context.main(modern)["proxy-groups"].length, 1);
assert.throws(() => context.main({ proxies: [], rules: [] }), /可用的代理节点/);
console.log("Clash Verge override smoke tests passed");
