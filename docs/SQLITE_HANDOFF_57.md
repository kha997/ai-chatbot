# Durable synthetic handoff and consent

[Issue #57](https://github.com/kha997/ai-chatbot/issues/57) authorizes one local, synthetic SQLite PR. Accepted baseline is PR #56 at 7da8524c5cb674197423a97684601cdafe4946c3, with 59/59 tests. The default in-memory adapter, quote fixtures, quote calculations and Developer Preview retain their accepted behavior.

## Try the restart demonstration

From the PR checkout on Windows, run:

```powershell
py -B -m unittest discover -s tests -p test_quote_sqlite.py -k new_python_process -v
```

The test creates a disposable SQLite file, queues two synthetic NHD tickets and withdraws consent for one. A separate Python process opens the same file with a new authority and newly issued synthetic staff handle. It delivers the still-consented ticket and sees an empty queue on the next call. The temporary directory is removed by the test.

Trusted Python setup can use SQLiteSessionQuotes(authority, path, clock=...) from scripts.quote_sqlite. Give it a dedicated local .sqlite, .sqlite3 or .db path and an existing parent directory. The authority is the one from scripts.quote_sessions. The separate wall clock supplies UTC Unix seconds. The Windows preview still starts with py -B -m scripts.quote_preview and uses the existing in-memory demo.

## Storage and authorization

- Schema version 1 uses an application ID and SQLite user_version. Initialization is atomic and rejects an unrelated populated or unknown-version DB. Normal operations open existing files and close connections after each operation. There is no migration of existing files.
- The consents table stores tenant, opaque ticket ID, fixed scope synthetic-quote-support version 1, grant/expiry times and an optional withdrawal timestamp. The tickets table stores tenant, that ID, an internally generated session correlation, bounded static reason/state, a SHA-256 message reference digest and a SHA-256 digest of the canonicalized bounded request. The tenant-qualified foreign key and unique tenant/session/message key link consent and enforce idempotency.
- No bearer handle, confirmation proof, actor name, raw request or source/price material is stored. Digests deduplicate requests. They are not encryption or privacy protection for low-entropy input. Keep this database synthetic.
- Every operation resolves a live bearer through the Issue #55 authority with a fixed role. Tenant in the call is an expected scope. Customer reads and withdrawal also require the original server-generated session correlation. Staff views and writes constrain tenant. Wrong tenant, role, session or ticket receive the same denial. The server checks the session again after entering the SQLite transaction.
- No customer re-binding is provided. Reopening the store in the same live authority preserves same-session idempotency. Restarting the application creates a new authority and permanently invalidates old handles. A new session with the same actor string has no claim to old tickets, and submitting a new consented request from it creates a distinct request. After full restart, the same-tenant synthetic support path can resume active tickets. Cross-restart customer resumption, including customer-initiated withdrawal of a historical ticket, requires a separately approved identity and recovery boundary.
- A delivered ticket's confirmation proof is derived using a process-local random key and bound to the ticket, tenant and current support session. After reopen, staff obtains a fresh proof from the authorized inbox. Confirmation also checks the persisted state and consent inside the write transaction.

## Consent and failure behavior

| Operation | Result |
| --- | --- |
| Clarification with literal true consent | Insert one grant and one queued ticket in a transaction |
| Same key and payload with active consent | Return existing ticket and state |
| Same key with changed payload, or withdrawn/expired consent | Deny. A fresh message reference and explicit consent are required |
| Same-tenant support delivery and confirmation | Queued → delivered → accepted. Reconfirming with a valid proof while consent is active is idempotent |
| Customer withdraws queued/delivered consent | Record withdrawal and cancel atomically, then exclude from delivery and confirmation |
| Customer withdraws accepted consent | Retain accepted history and withdrawal, remove from future staff views and confirmation. This does not undo the earlier mock acceptance |

Consent is active when granted_at <= UTC now < expires_at, for 24 hours at whole UTC-second precision. Session TTL is separately measured by the monotonic process clock. Expired consent is filtered on each operation without storing an additional expiration event. The wall clock is trusted and should not be rolled back. Withdrawal is terminal regardless of clock changes. Each new request needs its own grant.

Parameterized SQL and BEGIN IMMEDIATE serialize writers. Connections enable foreign keys and full synchronous commits with a two-second busy timeout. A SQLite error rolls back the transaction and returns a detail-free unavailable result. Retrying the identical authorized submission is safe if its consent is active. Rollback tests force an error between the two writes during both enqueue and withdrawal. The demo retains terminal rows as duplicate tombstones and caps each tenant at 1,000 tickets, then fails closed for new requests. There is no automatic eviction. For disposal, stop all demo callers and delete only the dedicated synthetic database and its own SQLite sidecars. The existing in-memory path is the rollback option.

Local file access and the Python fixture setup are trusted. This is an orderly restart and transaction-rollback demonstration, with no power-loss testing, at-rest encryption, production backups or retention guarantee. Developer Preview is a curated harness outside the SQLite boundary. Real identity, infrastructure, data, external delivery, AI, Agent Dispatcher, Gate 2 and production remain outside approval.

## Evidence

- Baseline and Windows full suite: py -B -m unittest discover -s tests -p 'test_quote*.py'. Baseline 59/59. With SQLite 73/73 (14 new tests).
- WSL no-egress: enter an isolated user and network namespace using unshare --user --map-root-user --net, enable only loopback via ip link set lo up, and run python3 -B -m unittest discover -s tests -p 'test_quote*.py' -v from the isolated worktree. 73/73. The preview HTTP regressions use only loopback.
- New tests use disposable SQLite files, injected clocks, independent SQLite connections for same-key contention, and a separate Python process for restart. No live or unrelated dispatcher/model tests were run.
- Independent Codex review and final CI pending.
