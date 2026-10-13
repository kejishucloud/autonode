# AutoNode 法律声明与风险提示
# Legal Notice & Disclaimer

> 本文件说明 AutoNode 的开源许可、软件风险和部署运营合规责任。**任何免责声明均不能保证使用者或开发者不存在法律风险，也不能排除适用法律不允许排除的责任。**
>
> This document describes the license, software risks, and compliance responsibilities associated with AutoNode. **No disclaimer eliminates all legal risk or excludes liability that cannot lawfully be excluded.**

## 中文

### 1. 项目性质

AutoNode 是公开发布的开源软件，提供服务器环境检测、代理节点配置、用户凭证与订阅管理等技术功能。公开源代码、技术文档或示例配置，**不代表**项目维护者授权任何违法用途，也不代表对使用者实际部署行为的合法性作出判断或保证。

项目与任何第三方云服务商、网络运营商或客户端软件提供方不存在当然的代理、背书或担保关系。

### 2. 使用者及运营者的合规责任

下载、部署、修改、分发或运营本项目的个人和组织，应当根据其**所在地、服务器所在地、服务对象所在地以及实际业务开展地**的适用法律，自行判断相关行为是否合法，并取得所需的授权、许可、备案或其他资质（如适用）。

需要特别核查的事项包括但不限于：

- 网络接入、跨境联网、代理服务、电信业务及相关许可或备案要求；
- 为第三方提供服务、收费或公开运营所涉及的法律义务；
- 网络安全、数据保护、个人信息处理、日志与留存、事件响应要求；
- 服务器托管商、域名注册商及其他第三方服务的使用条款；
- 相关地区适用的加密技术、出口管制及其他监管限制。

**个人自用、非营利或开源发布，不当然意味着某一具体部署或运营行为合法。** 如计划面向公众、收费或持续向第三方提供网络连接服务，应在上线前咨询具备相关执业资格的法律专业人士，并核实当地监管要求。

### 3. 合法使用与不得滥用

本项目应仅用于拥有适当权限且符合适用法律的场景，不应用于未经授权的网络访问、攻击、欺诈、恶意软件传播、侵犯他人隐私或知识产权、规避依法适用的安全管控，以及其他违法活动。

本节属于合法合规提示，**并不构成对 MIT License 所授予软件著作权许可范围的额外限制**；各方仍须遵守适用法律。

### 4. 安全、隐私与运营风险

部署者负责自身基础设施及服务的配置、访问控制、密钥和订阅令牌保护、补丁更新、监控、事件处理、数据治理和必要的信息告知。订阅 URL、二维码、UUID、密钥等可能属于访问凭证，不应公开到仓库、Issue、日志或截图。

使用无 HTTPS 保护的 HTTP 订阅可能使订阅内容和令牌在传输过程中暴露。提供服务前，运营者应按实际处理的数据、适用法律及业务模式完成必要的隐私与安全评估。本项目的提供不意味着作者替部署者承担托管、用户支持、数据保护或事故处置义务。

### 5. 软件按现状提供与责任限制

本项目依据仓库中的 [MIT License](LICENSE) 授权。**在适用法律允许的最大范围内**，软件按“现状”（AS IS）提供，不提供关于适销性、特定用途适用性、不侵权、持续可用性、安全性、性能、兼容性或符合法律法规的明示或默示保证。

对因使用、无法使用、修改或运营本项目导致的损失及争议，相关责任应依实际行为、适用法律与具体事实认定。项目维护者和贡献者不因开源发布本身对第三方运营活动提供保证或承担其依法应由运营者承担的义务；**任何责任排除均以适用法律允许为限**，不得解释为免除法律明确规定不得免除的责任。

### 6. 第三方项目与独立权利

AutoNode 可能安装或调用 sing-box、Caddy 及其他第三方软件、API 和服务。它们各自的许可证、商标、使用条件和安全维护责任独立适用。本仓库的 MIT License 不替代第三方许可证，也不意味着第三方对本项目作出认可或担保。

### 7. 非法律意见

本说明为一般性风险提示，**并非针对特定司法辖区或使用场景的法律意见**。法律及监管要求会变化，如有合规疑问，应向当地合格律师或主管机关核实。发现明确的安全问题时，请避免在公开 Issue 中提交凭证、真实用户数据或服务器私密信息。

---

## English

### 1. Project scope

AutoNode is open-source software for server detection, proxy-node configuration, credentials, and subscription management. Publication of source code and documentation does not authorize unlawful activity or constitute a representation that any particular deployment or operation is lawful. There is no implied endorsement, agency, or warranty from hosting providers, network operators, or third-party client vendors.

### 2. Legal compliance

Each user, deployer, distributor, and service operator is responsible for evaluating laws and regulations applicable to their location, their server, their users, and their activities, including any required authorizations, licenses, registrations, or filings. Relevant rules may concern telecommunications and cross-border connectivity, commercial services, cybersecurity, privacy, data retention, hosting terms, cryptography, and export controls.

**Personal, non-commercial, or open-source use is not necessarily lawful in every jurisdiction.** Before making connectivity services available to the public, charging users, or operating services for others, seek qualified local legal advice and verify regulatory requirements.

### 3. Lawful use

Use the software only with appropriate authorization and in compliance with applicable law. Do not use it for unauthorized access, attacks, fraud, malware distribution, privacy or intellectual-property violations, or other unlawful activity. This section is compliance guidance **not an additional restriction on the copyright permissions granted by the MIT License**.

### 4. Security and privacy

Operators are responsible for system security, access control, subscription-token and key protection, maintenance, incident handling, data governance, and any legally required notices. Subscription URLs and QR codes may contain credentials. Plain HTTP subscriptions may expose credentials in transit. Authors do not undertake the operator's hosting, user-support, data-protection, or incident-response responsibilities.

### 5. Warranty and liability

AutoNode is licensed under the repository's [MIT License](LICENSE) and provided **“AS IS”**, without express or implied warranties, to the fullest extent permitted by applicable law. No availability, security, fitness, compatibility, non-infringement, or legal-compliance outcome is guaranteed.

Responsibility for a particular use or operation depends on the actual conduct, facts, and applicable law. No disclaimer excludes liabilities that cannot legally be excluded or protects a party from its own unlawful conduct.

### 6. Third parties

sing-box, Caddy, and other dependencies and services retain their own licenses, policies, and rights. The AutoNode license does not supersede them, and their inclusion does not imply endorsement.

### 7. Not legal advice

This document provides general information, **not jurisdiction-specific legal advice**. Consult a qualified local legal professional for a concrete deployment or service model. Do not post secrets or personal data in public issue reports.
