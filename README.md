# AI ChatBot — Multi-Website AI Agent Platform

Independent research and engineering repository for a reusable, multi-tenant AI chatbot/agent platform serving:

- **NHD:** commerce, product guidance, and quotation journeys
- **HANU:** translation service enquiries and customer support
- **ZENA:** architecture/design enquiries and lead qualification

## Current mandate

**Research and evaluation only.** Compare Langflow, LangGraph, RAGFlow, Chatwoot and Mem0 using a shared, synthetic benchmark. Do not deploy to production, connect live business sites, process real customer data, activate paid providers, or alter repositories belonging to NHD/HANU/ZENA.

## How work is organized

- The GitHub repository is the durable source of truth; the local workspace is `D:\Projects\AI ChatBot`.
- Read [AGENTS.md](AGENTS.md) for delegated autonomy, safety boundaries, review and reporting requirements.
- Keep [docs/STATUS.md](docs/STATUS.md) accurate and comprehensible to a non-technical Owner.
- Work on short-lived branches and open pull requests with verifiable evidence.
- Write decisions, limitations, and results to GitHub; local-only files, unpushed branches and chat summaries do **not** count as delivered work.
- Start with the [project kickoff issue](https://github.com/kha997/ai-chatbot/issues) and progress through the research gates without technical-choice escalations to the Owner.

## Gate 0–1 research package

- [Owner brief (Vietnamese)](docs/OWNER_BRIEF.md)
- [OSS evidence and licenses](docs/OSS_DUE_DILIGENCE.md)
- [Recommended architecture and A/B alternative](docs/ARCHITECTURE.md)
- [Tenant threat model and learning governance](docs/SECURITY_AND_MEMORY.md)
- [Synthetic evaluation and scoring specification](docs/EVALUATION_SPEC.md)
- [Widget, mock handoff and cost/operations protocol](docs/INTEGRATION_AND_OPERATIONS.md)
- [Observed CLI capabilities and dispatcher design](docs/AGENT_DISPATCHER_DESIGN.md)

All runtime results remain NOT_RUN. Read [status](docs/STATUS.md) for reviewed commits and the current gate decision.

## Product principles

One reusable core, multiple strictly isolated tenants. Retrieval grounded in approved evidence. Memory and learning only through governed promotion. Human takeover when needed. Provider portability, observability, reversible changes and safe defaults.

## Public-repository rule

This repository is currently **public**. Commit only synthetic/public/licensed content. No credentials, real customer information, proprietary business documents, or data copied from private repositories. Before expanding into real integrations, reassess repository visibility and data access at an explicit Owner Gate.
