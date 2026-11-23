# Issue #59 — source and uncertainty ledger

Checked **2026-11-23 (Asia/Saigon)** through public official pages and the GitHub connector. No model/API inference, signup, private repository, business data or live service was used. URLs are citations, not instructions to execute examples. Vendor capabilities/prices are not local benchmark results. Dynamic pages may change; recheck before any installation or spend. No third-party source code is copied into this dossier.

## Repository baseline

| Evidence | Observation |
| --- | --- |
| [Issue #59](https://github.com/kha997/ai-chatbot/issues/59) | Explicit docs-only, one PR, independent review, Architecture Acceptance before merge |
| [main commit](https://github.com/kha997/ai-chatbot/commit/6243aa7806b9209e3df810fbe34f1dab7bc51a40) | `git fetch origin main` resolved to this SHA; all code inventory is bound to it |
| [PR #56](https://github.com/kha997/ai-chatbot/pull/56) | API `merged=true`; merge `7da8524c5cb674197423a97684601cdafe4946c3`, 2026-11-22 23:54:56 UTC (November23 local) |
| [PR #58](https://github.com/kha997/ai-chatbot/pull/58) | API `merged=true`; merge `6243aa7806b9209e3df810fbe34f1dab7bc51a40`, 2026-11-23 04:50:18 UTC; historical 73/73 and independent review receipt |
| [Issue #46 record at baseline](https://github.com/kha997/ai-chatbot/blob/6243aa7806b9209e3df810fbe34f1dab7bc51a40/docs/DIRECT_OLLAMA_READINESS_46.md) | Historical available RAM/GPU-confinement blockers; not current machine telemetry |

## Orchestration and optional modules

Release endpoints `/repos/{owner}/{repo}/releases/latest` were reread for all five projects; dates/tags match the prior dossier. This does not resolve every independently versioned package. Pinned root licenses below were reread. Source SHAs are retained from the previously reviewed [OSS dossier](OSS_DUE_DILIGENCE.md); pinned content was accessible. Latest release is an observation, not an installation recommendation or full dependency lock.

| Component | Release observation / source SHA | License evidence and scoped conclusion |
| --- | --- | --- |
| LangGraph | [1.2.24](https://github.com/langchain-ai/langgraph/releases/tag/1.2.24), Nov20; `58a6e1cc5b7dfc3619fc6e7e7573b040d554649b` | [MIT](https://github.com/langchain-ai/langgraph/blob/58a6e1cc5b7dfc3619fc6e7e7573b040d554649b/LICENSE); retain notices; no hosting/multi-tenant restriction in inspected OSS license; not a LangSmith/server entitlement |
| Langflow | [v1.13.3](https://github.com/langflow-ai/langflow/releases/tag/v1.13.3), Nov17; `55c4398326671f35c3a8d48a24e8243ab2b92f5b` | [MIT](https://github.com/langflow-ai/langflow/blob/55c4398326671f35c3a8d48a24e8243ab2b92f5b/LICENSE); notices required; service/connector rights separate |
| RAGFlow | [v1.0.0](https://github.com/infiniflow/ragflow/releases/tag/v1.0.0), Nov6; `db1cd5929a7885a3074547791f5ecc4d2f891739` | [Apache-2.0](https://github.com/infiniflow/ragflow/blob/db1cd5929a7885a3074547791f5ecc4d2f891739/LICENSE); license/NOTICE/change attribution and patent/trademark conditions apply; no whole-image clearance |
| Mem0 | Latest endpoint returns [TS v3.3.1](https://github.com/mem0ai/mem0/releases/tag/ts-v3.3.1), Sep25; prior Python observation v2.2.1, same `94c3fe9f238f3dbf29c9ce98643bd71eb13077cd` | [Apache-2.0](https://github.com/mem0ai/mem0/blob/94c3fe9f238f3dbf29c9ce98643bd71eb13077cd/LICENSE); same notice caveats; managed platform excluded. Python release freshness not independently re-queried here |
| Chatwoot | [v4.20.1](https://github.com/chatwoot/chatwoot/releases/tag/v4.20.1), Nov20; `b2f94636d325a126a67c6c4c808303d8aa8cbeea` | [Root license](https://github.com/chatwoot/chatwoot/blob/b2f94636d325a126a67c6c4c808303d8aa8cbeea/LICENSE) separates MIT Community from third-party and enterprise code. [Enterprise license](https://github.com/chatwoot/chatwoot/blob/b2f94636d325a126a67c6c4c808303d8aa8cbeea/enterprise/LICENSE) requires production entitlement; excluded |

Scoped license assessment is technical due diligence, not legal approval to accept terms. No paid/enterprise agreements accepted. Exact selected SDK, ASGI server, DB driver, images, model weights/tokenizer, fonts and transitive licenses remain UNKNOWN until a later lock/SBOM review. No root project LICENSE was found at the baseline; public visibility alone does not grant third parties a reuse license. Owner retains legal/licensing decisions before external distribution.

| Primary capability/security source | Fact used / decision consequence |
| --- | --- |
| [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview), [persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Explicit state/graphs, checkpoints and human interruption support long-lived flows. Engineering inference: defer until narrow MVP needs those capabilities; persistence is not authorization |
| [Langflow security 1.13.x](https://docs.langflow.org/security) | IDE can execute code; shared process does not isolate users/disk/network. Requires infrastructure isolation; not an exposed customer authoring surface |
| [LangGraph GHSA-6hmw-9432-67qq](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-6hmw-9432-67qq) | Namespace-label collision; Postgres <3.1.3 and SQLite <3.1.2 affected. Checkpoint package floors are not a complete current scan; verify every read/search/delete/batch surface |
| [RAGFlow GHSA-wpg4-h5g2-jxm6](https://github.com/infiniflow/ragflow/security/advisories/GHSA-wpg4-h5g2-jxm6) | Advisory lists <=0.24.0 and no patched version. Applicability to rewritten1.0.0 remains UNKNOWN; exclude pending exact code/fix mapping |

GitHub connector did not support the security-advisory API path; official advisory web pages were read instead. Other advisories in the November21 dossier are historical evidence, not rechecked-all claims. No dependency scanner was run. Recent releases show maintenance activity, not a support SLA. Framework upgrades, migrations and security patching need an accountable engineer; zero license fee is not zero operating cost.

## Inference, data and price evidence

| Source / exact documented identifier | Observation used |
| --- | --- |
| [GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini.md) — `gpt-5.4-mini-2026-03-17` | Text input/output; structured outputs/function calling; reasoning `none` supported. Standard $0.75/M input, $4.50/M output; cached input $0.075 not assumed in budgets. Regional processing +10% where applicable. Proposed candidate, not verified account access or Vietnamese quality |
| [GPT-6.1 Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra.md) — `gpt-6.1-terra` | $1/M input, $5/M output; structured outputs; tool calling via Responses. No dated snapshot listed on fetched page; do not invent a pin. Candidate alternative only |
| [GPT-5 mini](https://developers.openai.com/api/docs/models/gpt-5-mini.md), [deprecations](https://developers.openai.com/api/docs/deprecations.md) | Deprecated; shutdown listed Dec11,2026. Do not choose it for a new MVP despite lower old rates |
| [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) redirected to [official AI Studio pricing](https://aistudio.google.com/docs/pricing) — `gemini-3.5-flash-lite` | Standard $0.30/M input, $2.50/M output including thinking. Free/paid data-use treatment differs. Gemini2.5 Flash routing changes Dec1,2026; not a new default. Exact immutable model revision/account entitlement UNKNOWN |
| [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data.md) | API data not used for training by default absent opt-in; abuse monitoring can retain content up to30 days with exceptions. `store:false` is not zero retention. ZDR eligibility requires approval; no such approval assumed |
| [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small.md) | $0.02/M embedding input tokens. Optional hybrid-retrieval cost example only; not used or approved |
| [Ollama FAQ](https://docs.ollama.com/faq), [Qwen3-14B upstream card](https://huggingface.co/Qwen/Qwen3-14B) | Context/parallelism affects resource requirements; model card identifies Apache-2.0. Stored quantized artifact/license lineage and runtime feasibility still require qualification; card is not proof of the local artifact or its performance |

No benchmark or vendor marketing quality percentage is treated as NHD evidence. Price comparison uses identical assumed tokens for arithmetic only; actual tokenizers, reasoning, errors and number of calls can differ. API/provider regional availability, current quotas, hard spending enforcement, local law, DPA/transfer basis and contractual retention obligations are UNKNOWN and gated before activation. This review makes no legal-compliance claim.

## Storage and deployment evidence

| Source | Observation used |
| --- | --- |
| [PostgreSQL version policy](https://www.postgresql.org/support/versioning/) |18.7 is the current minor of supported18 on check date;19.0 newly released Nov19. Prefer established supported18 for pilot, recheck patch before install. Major migration needs explicit rehearsal |
| [PostgreSQL license](https://www.postgresql.org/about/licence/) | Permissive PostgreSQL license, retain required notices; no managed-service entitlement |
| [PostgreSQL18 text search](https://www.postgresql.org/docs/18/textsearch-intro.html) | Built-in indexed lexical search; does not establish Vietnamese recall; custom normalization/aliases need tests |
| [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) | Owners/superusers/BYPASSRLS can bypass policies; use constrained roles and test grants; tenant separation cannot rest on application filtering alone |
| [SQLite appropriate uses](https://sqlite.org/whentouse.html) | Embedded/local storage role differs from client/server concurrency and centralized access; current synthetic use is appropriate, production architecture needs separate reasoning |
| [pgvector README](https://github.com/pgvector/pgvector), [v0.8.1 license](https://raw.githubusercontent.com/pgvector/pgvector/v0.8.1/LICENSE) | Optional Postgres vector search; inspected license is PostgreSQL-style. v0.8.1 is a license reference, not claimed latest or an approved runtime pin; exact extension compatibility/security version remains future qualification |
| [DigitalOcean Droplets](https://www.digitalocean.com/pricing/droplets) | Basic regular2-vCPU/4-GiB $24/month,4-vCPU/8-GiB $48/month; daily percentage backup30%. Used as public price anchors only, not procurement/region/capacity promises |

## Missing evidence that must remain explicit

Real NHD catalog/units/price/tax/rounding/stock policy, rights and publication approval; expected traffic and seasonality; customer-device/network mix; operator capacity; approved provider account/billing cap; exact deployment region and privacy terms; measured Vietnamese QA/recall/latency/tokens/RAM; dependency lock/transitive licenses/advisory scan; production identity, restore and deletion evidence. These unknowns do not block a coherent architecture recommendation, but block execution or real use at the gates specified in the [roadmap](NHD_MVP_COST_ROADMAP_59.md).
