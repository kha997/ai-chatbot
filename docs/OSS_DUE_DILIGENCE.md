# OSS due diligence

Access date for all evidence: **2026-11-21**. Research: built-in Codex `oss_research`; synthesis: lead Codex. Official release APIs, tag commits, pinned licenses and upstream advisories were read. No products were installed or benchmarked. Conclusions concern the inspected OSS scope, not legal commitments or whole-stack certification.

## Version inventory

| Component / role | Observed release (publication date) | Resolved source commit |
| --- | --- | --- |
| Langflow / orchestration A | [v1.13.3](https://github.com/langflow-ai/langflow/releases/tag/v1.13.3) (2026-11-17) | `55c4398326671f35c3a8d48a24e8243ab2b92f5b` |
| LangGraph / orchestration B | [1.2.24](https://github.com/langchain-ai/langgraph/releases/tag/1.2.24) (2026-11-20) | `58a6e1cc5b7dfc3619fc6e7e7573b040d554649b` |
| RAGFlow / optional document retrieval | [v1.0.0](https://github.com/infiniflow/ragflow/releases/tag/v1.0.0) (2026-11-06) | `db1cd5929a7885a3074547791f5ecc4d2f891739` |
| Mem0 Python / optional memory | [v2.2.1](https://github.com/mem0ai/mem0/releases/tag/v2.2.1) (2026-09-25) | `94c3fe9f238f3dbf29c9ce98643bd71eb13077cd` |
| Mem0 TypeScript / alternate SDK | [ts-v3.3.1](https://github.com/mem0ai/mem0/releases/tag/ts-v3.3.1) (2026-09-25) | Same source commit as Python |
| Chatwoot / optional human inbox | [v4.20.1](https://github.com/chatwoot/chatwoot/releases/tag/v4.20.1) (2026-11-20) | `b2f94636d325a126a67c6c4c808303d8aa8cbeea` |

These are observation-time releases, not a reproducible deployment lock. GitHub `/releases/latest` for Mem0 returns the TypeScript release; Python and TypeScript numbers must not be conflated. LangGraph checkpoint/SDK/CLI packages are independently versioned. Revalidate releases/advisories when Gate 2 is authorized; record exact resolved dependencies and image digests before executing.

## Licenses and commercial boundaries

| Scope | Pinned primary evidence | Assessment |
| --- | --- | --- |
| Langflow | [MIT](https://github.com/langflow-ai/langflow/blob/55c4398326671f35c3a8d48a24e8243ab2b92f5b/LICENSE) | Inspected license contains no hosting/multi-tenant prohibition; preserve notices. Connector/model/service rights remain separate. |
| LangGraph OSS library | [MIT](https://github.com/langchain-ai/langgraph/blob/58a6e1cc5b7dfc3619fc6e7e7573b040d554649b/LICENSE) | Same scoped conclusion; do not extend it to hosted LangSmith or separately licensed server/deployment products. Those entitlements are UNKNOWN/not approved. |
| RAGFlow | [Apache-2.0](https://github.com/infiniflow/ragflow/blob/db1cd5929a7885a3074547791f5ecc4d2f891739/LICENSE) | No hosting/multi-tenant prohibition in inspected license. Preserve applicable license/NOTICE, mark distributed modifications and respect patent/trademark conditions. |
| Mem0 OSS | [Apache-2.0](https://github.com/mem0ai/mem0/blob/94c3fe9f238f3dbf29c9ce98643bd71eb13077cd/LICENSE) | Same scoped conclusion; managed Mem0 Platform terms are separate and not approved. |
| Chatwoot Community | [Root license](https://github.com/chatwoot/chatwoot/blob/b2f94636d325a126a67c6c4c808303d8aa8cbeea/LICENSE) | MIT except explicitly excluded `enterprise/` and third-party materials. CE-only is the proposed scope. |
| Chatwoot Enterprise | [Enterprise license](https://github.com/chatwoot/chatwoot/blob/b2f94636d325a126a67c6c4c808303d8aa8cbeea/enterprise/LICENSE) | Proprietary scope with production subscription/license and redistribution constraints. Excluded; public code visibility is not OSS permission. |

The [Chatwoot edition guide](https://app.chatwoot.com/hc/user-guide/articles/1677776492-enterprise-edition) distinguishes Community and Enterprise. Do not assume an enterprise feature is included in CE. Before reuse: inventory actual locked libraries, databases, images, parsers/OCR/embedding models, fonts and widget assets; record license/version/source/NOTICE and distribution obligations. No full transitive audit or legal clearance has been performed. No paid terms accepted.

## Capabilities and limitations by role

- **Langflow:** visual authoring and API/MCP serving ([pinned README](https://github.com/langflow-ai/langflow/blob/55c4398326671f35c3a8d48a24e8243ab2b92f5b/README.md)). Its [security guidance](https://docs.langflow.org/security) explicitly rejects shared-process tenant isolation; flow visibility does not enforce security. External authorization and process/disk/network/database isolation are required. Keep IDE private to trusted engineers.
- **LangGraph:** explicit state, nodes/edges, persistence, streaming and human intervention ([official overview](https://docs.langchain.com/oss/python/langgraph/overview)). These mechanisms fit auditable application policy transitions; they do not supply the business authorization rules. The proposal uses the Python OSS library, not a hosted control plane.
- **RAGFlow:** optional complex-document pipeline. Version 1.0.0 is a Go rewrite; old Python-stack deployment assumptions are stale. The [pinned README](https://github.com/infiniflow/ragflow/blob/db1cd5929a7885a3074547791f5ecc4d2f891739/README.md) gives a starting point of 4 CPU cores, 16 GB RAM and 50 GB free disk; actual workload capacity is UNKNOWN. CPU DeepDoc support does not imply all model work is free or local. Upstream performance claims are not our measurements.
- **Mem0:** [OSS overview](https://docs.mem0.ai/open-source/overview) describes library/server options and configurable LLM/embedder/vector store. Defaults may invoke external models. Evaluate extraction costs and poisoning/deletion semantics against simple structured preferences; do not run credentialed examples now.
- **Chatwoot:** inbox/handoff component, not a replacement for retrieval or orchestration. Its [security policy](https://github.com/chatwoot/chatwoot/security) supports the latest release, implying ongoing upgrade effort. Include worker/queue/transcript/notification operations and human staffing costs. Capacity remains UNKNOWN.

## Representative upstream security evidence

This is a targeted advisory review, not a complete vulnerability scan. Patched floors below are historical evidence, not a sufficient install specification.

| Component | Official advisory and observed applicability | Required response |
| --- | --- | --- |
| Langflow | [GHSA-cf6m-vc3m-7cgm](https://github.com/langflow-ai/langflow/security/advisories/GHSA-cf6m-vc3m-7cgm): webhook auth bypass, affected 1.7.0–1.9.0, patched 1.9.1 | Flow UUID is not authorization; test anonymous/wrong-tenant execution and disabled-auth drift. |
| LangGraph checkpoint stores | [GHSA-6hmw-9432-67qq](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-6hmw-9432-67qq): delimiter collision; Postgres patch 3.1.3, SQLite 3.1.2, checkpoint 4.3.0 prerequisite | Canonical IDs, independent storage credentials; test read/search/delete/batch, not only writes. |
| LangGraph SDK | [GHSA-fvww-7h3r-vfhp](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-fvww-7h3r-vfhp): action authorization registered too broadly, 0.1.45–0.4.3 affected, 0.4.4 patched | Test every resource/action combination. Applies to affected SDK behavior, not a blanket claim against all library use. |
| LangGraph API / JS auth | [GHSA-4hm6-w6qq-w73v](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-4hm6-w6qq-w73v): namespace rewriting issue, API patch 0.15.0 | Conditional API/JS applicability; Python library default avoids this optional surface, not all risks. |
| RAGFlow | [GHSA-wpg4-h5g2-jxm6](https://github.com/infiniflow/ragflow/security/advisories/GHSA-wpg4-h5g2-jxm6): authenticated template RCE, lists <=0.24.0 and no patch | Applicability to rewritten 1.0.0 UNKNOWN. Optional RAGFlow runtime is blocked until source/fix mapping resolves it. A greater version number alone is insufficient. |
| Mem0 | [GHSA-5324-3w58-qpp2](https://github.com/mem0ai/mem0/security/advisories/GHSA-5324-3w58-qpp2): delimiter collision/raw-message leakage; patch Python 2.0.18/npm 3.1.6 | Header ranges conflict with vulnerable versions in body (2.0.14/3.1.2). Use conservative patch evidence, resolve exact package applicability and test adversarial identifiers. |
| Chatwoot | [GHSA-x288-jh8j-348c](https://github.com/chatwoot/chatwoot/security/advisories/GHSA-x288-jh8j-348c): mutable account_id cross-account transfers, patch 4.9.0 | Server-bind account/inbox and test malicious tenant admin resource reassignment. |

LangGraph's [pinned manifest](https://github.com/langchain-ai/langgraph/blob/58a6e1cc5b7dfc3619fc6e7e7573b040d554649b/libs/langgraph/pyproject.toml) specifies Python >=3.10, checkpoint >=4.3.0,<5, SDK >=0.4.6,<0.5 and prebuilt >=1.1.3,<1.2. Dependency ranges are not a lockfile or scan. Tenant isolation still requires defense outside these libraries.

## Maintenance and operational assessment

November releases show active changes for Langflow, LangGraph, RAGFlow and Chatwoot; Mem0 has a September release. Recency is evidence of activity, not a support SLA, bus-factor score or quality benchmark. Langflow release notes include policy/session/security fixes; LangGraph includes checkpoint/message handling changes; Chatwoot updates runtime hardening; RAGFlow's major rewrite adds migration uncertainty. Exact staffing, upgrade hours, deployment footprint (except cited starting guidance), backup reliability and cost remain unmeasured.

Decision: choose **B: LangGraph OSS** for explicit, code-reviewed policy transitions and application-owned authorization. This is engineering inference from documented primitives and project requirements, not a measured superiority claim. Retain **A: Langflow** as controlled visual alternative; compare both with identical functional contracts. Defer RAGFlow/Mem0/Chatwoot to separate incremental evaluations. See [architecture](ARCHITECTURE.md), [security](SECURITY_AND_MEMORY.md) and [evaluation](EVALUATION_SPEC.md).
