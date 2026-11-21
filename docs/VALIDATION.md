# Gate 0–1 validation evidence

Date: 2026-11-21. Executor: lead Codex. Scope: static research artifacts only. Runtime model, isolation, performance, cost and handoff tests are **NOT_RUN**.

## Observed checks

| Check | Subject | Observation |
| --- | --- | --- |
| Local reconciliation | Initially empty `D:\Projects\AI ChatBot` | No files or Git history overwritten; clone succeeded; baseline 237984c966c6fd5070b04e2166494a873f882920 |
| Governance review | PR #2 head f532e0a48ea11d82b2549424c9f0e2b2e777ef38 | Separate Codex reviewer; three findings corrected; diff whitespace passed; merge 919b018045abd88e45a3ca7716643a48d25a5ce8 |
| Discovery | Windows + existing running Ubuntu-24.04 | [Capability matrix](AGENT_DISPATCHER_DESIGN.md); OpenCode 1.18.30 help/version exit 0; no prompt calls |
| Static package check | Content committed as b29f3e8ac52d135ea3d2f469246d9f0dac8571b9 | PASS: 33 local Markdown targets; 3 JSON source/oracle pairs; synthetic labels; tenant/citation consistency; exact arithmetic; null result values |
| Evaluation arithmetic | Same package | 348 scenarios; 1,044 executions/candidate for 3 repetitions; load 2,700 requests/candidate; score weights sum 100% |
| Whitespace | `git diff --check` before package commit | Exit 0 |
| Release verification | Five official GitHub release/tag APIs, independently repeated by lead | Exact dates/SHAs below match OSS dossier |

Example JSON SHA-256 (UTF-8 LF bytes): `46dbf607a7100cd7562c90112eb7e361546c79e78a7625bbdb1ef86064a521bc`. This identifies the example, not a full frozen benchmark. Git may change checkout line endings; authoritative hash is over committed blob bytes.

| Repo / tag | API publication UTC | Resolved source SHA |
| --- | --- | --- |
| langflow-ai/langflow v1.13.3 | 2026-11-17T21:22:27Z | 55c4398326671f35c3a8d48a24e8243ab2b92f5b |
| langchain-ai/langgraph 1.2.24 | 2026-11-20T01:10:26Z | 58a6e1cc5b7dfc3619fc6e7e7573b040d554649b |
| infiniflow/ragflow v1.0.0 | 2026-11-06T12:31:31Z | db1cd5929a7885a3074547791f5ecc4d2f891739 |
| mem0ai/mem0 v2.2.1 | 2026-09-25T17:35:20Z | 94c3fe9f238f3dbf29c9ce98643bd71eb13077cd |
| chatwoot/chatwoot v4.20.1 | 2026-11-20T08:29:49Z | b2f94636d325a126a67c6c4c808303d8aa8cbeea |

Reproduction uses public endpoints `https://api.github.com/repos/{repo}/releases/tags/{tag}` and `/commits/{tag}`. Sources and license/advisory URLs are in [OSS dossier](OSS_DUE_DILIGENCE.md); no credential is required for these reads, subject to public rate limits. These checks are not a transitive vulnerability or license audit.

## Reproduce static validation

Run Python from repository root (standard library only). The following is the equivalent auditable validation logic used for this package; it neither starts services nor invokes a model:

```python
import json, re, pathlib, decimal, hashlib, subprocess
root = pathlib.Path('.')
links = 0
for p in [root/'README.md', root/'AGENTS.md', *root.glob('docs/**/*.md')]:
    for target in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8-sig')):
        if '://' in target or target.startswith('#'):
            continue
        links += 1
        assert (p.parent / target.split('#')[0]).exists(), (p, target)
blob = subprocess.check_output(['git', 'show', 'HEAD:eval/examples.json'])
data = json.loads(blob)
assert data['synthetic'] is True
assert len(data['documents']) == len(data['cases']) == 3
assert {c['tenant'] for c in data['cases']} == {'NHD', 'HANU', 'ZENA'}
assert len({c['id'] for c in data['cases']}) == 3
docs = {d['id']+'#'+d['paragraph']: d for d in data['documents']}
for c in data['cases']:
    d = docs[c['oracle']['citation']]
    assert c['synthetic'] and d['synthetic'] and c['tenant'] == d['tenant']
    assert d['authority'] == 'approved' and 'SYNTHETIC' in d['text']
    total = max(decimal.Decimal(c['quantity']) * decimal.Decimal(d['unit_price']),
                decimal.Decimal(d.get('minimum', '0')))
    assert total == decimal.Decimal(c['oracle']['total'])
    assert c['oracle']['currency'] == d['currency']
    assert c['oracle']['allowed_side_effects'] == []
r = data['result_template']
assert r['status'] == 'NOT_RUN'
assert all(r[k] is None for k in ('response', 'latency_ms', 'model_calls',
                                 'input_tokens', 'output_tokens', 'cost'))
assert 180+18+36+72+24+18 == 348 and 348*3 == 1044
assert 3*3*100*3 == 2700 and sum([10,35,15,20,10,10]) == 100
assert hashlib.sha256(blob).hexdigest() == '46dbf607a7100cd7562c90112eb7e361546c79e78a7625bbdb1ef86064a521bc'
print('PASS', links, 'local links; three examples; counts; committed hash')
```

Also run `git diff --check` and inspect `git diff --stat`/`git status --short`. Link check verifies local target existence, not heading anchors or universal availability of every upstream page. Manual review inspected staged content for real/private data, credentials and executable scope expansion; this is not an automated comprehensive secret scanner.

## Evidence limitations

No runtime benchmark, formal JSON Schema implementation/validator, complete corpus, SBOM, exploit reproduction, provider billing probe, browser accessibility test, production deployment or dispatcher exists in this deliverable. Static examples prove contract consistency only. Source pages may change after access date; pinned source links preserve inspected code/license identity. Separate reviewer findings and their disposition are recorded with immutable commits before Gate 1 closure.
