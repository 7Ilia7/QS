# QC local backend correction, 23 October 2026

Exact child evt-owner-513fc12254e755fb15d617da, parent43456f0ed903f454041d3455.
Owner-scoped local B1/B2 increment; independent review and release are separate.
See api-deployment-agreement.md for early frontend/deployment agreement and
Readmde.md for factual session result. Original frozen v1 is immutable; copied
original-manifest.json pins9original hashes, digest041306bbd38a046e1c992fd83a65e6de6bc4c596b0059c7299051b7d5b2b75a7.

## Runtime and tests

Stdlib Python3.12/3.13 POSIX; local3.12.5 verified. No pip/npm build/install.
backend/server.py is entrypoint; package.json is convenience metadata only.
From backend directory: `python3 -B -m unittest -v test_server test_correction`.
32 tests Passed,0 Failed,0 Skipped; raw output test-results.txt. External network
blocked; only explicit127.0.0.1 test connections permitted. Crash test subprocess
blocks external connections and exits77 after mocked positive Bot API result,
before receipt commit; restart verifies unknown/no resend for both types.

Production availability and release effects are NOT established by this child.
Deployment's prior bounded snapshot reports host Python3.12.3, not reverified by
backend. No SSH/server operations, actual API/messages or secret access here.

## Private ledger and synthetic receipts

Required runtime environment names: QS_STATE_DIR, QS_ORIGIN, QS_TELEGRAM_TOKEN,
QS_TELEGRAM_CHAT_ID; optional QS_TRUST_LOOPBACK_PROXY, QS_SYNTHETIC_PAIRS.
No values read from Keychain/env/private server files in this local task.
Existing reference metadata brainy.telegram.qs.bot.v1, selected @QST_help_bot,
exact target-4907639564; no migration/fallback route. Existing status route is
unmodified. Proposed protected file /etc/qs-forms/telegram.env0600 outsidewebroot
and proposed state /var/lib/qs-forms0700 remain unprovisioned by this child.
Identity/rights/credential safety need later authorized verification. Historical
exposed browser credential must not be copied/reused; no silent rotation.

Before any live acceptance, release QA freezes one random UUIDv4 callback and
one random UUIDv4 review (no IDs selected here) in its descriptor and environment
QS_SYNTHETIC_PAIRS JSON object. This is operator config, never public form data.
Exactly2 or zero configured; one per type. New ledger embeds declaration and
rejects config change or retroactive registration of already-used UUID. UI fixture
mechanism for these IDs requires separately reviewed frontend code/QA procedure.
No third synthetic receipt; ordinary customer body/token never persisted.

First-time initialization ONLY after authorized fresh-state verification:
`python3 -B server.py --initialize-state`; requires QS_STATE_DIR and desired
QS_SYNTHETIC_PAIRS injected by operator. Does not load token or open listener.
Refuses existing ledger. Start normally with `python3 -B server.py --port 8787`.
Normal start requires existing ledger; missing/corrupt ledger stops startup.
Never rerun initialization after state loss to force recovery/retry. Stop via
supervisor SIGTERM; pending turns unknown at restart, no automatic transport retry.
One writer enforced by flock. Preserve state/HMAC across restarts/code rollback;
never restore an older backup over new reservations, clear uncertain IDs or
replace UUID to evade ambiguity. No business DB/accounts/users/Reader.

Private outcomes.json0600 stores technical UUID/type/HMAC-digest/time/status and
opaque receipt as before; ONLY two predeclared records may additionally contain
provider_receipt{request_id,type,ok,message_id,target,timestamp,receipt_id}.
Reserve/spent marker fsync+atomic rename+directory fsync BEFORE network effect.
Delivered plus sanitized positive receipt commit as ONE atomic file replacement.
Failure to commit poisons current process state: unknown/no success/no new sends;
restart reads durable pending as unknown. Missing/malformed receipt on delivered
synthetic becomes unknown; spent marker also prevents resend if record is lost.
Entire ledger loss on restart fails closed. No guarantee against privileged
operator replacing the complete ledger with an older valid file; prohibited.

Only exact ok=true,positive integer message_id,exact target qualifies. Late result
after provider8s or application deadline is discarded, never saved as success.
Ambiguous timeout/network/5xx =>unknown. Definite parsed Bot API400/401/403/404/429
=>failed retry_safe=true. For acceptance quota, do not allocate replacement IDs
even after failure without separately reconciling evidence and owner procedure.
General API user retries require explicit action and NEW UUID only if safe.

Operator read-only receipt export AFTER separately authorized live QA:
`python3 -B inspect_receipts.py /var/lib/qs-forms/outcomes.json`.
Requires private path/file, no network/env access/writes. Outputs exactly2
sanitized receipt rows or unknown rows, never customer records,HMAC key,digest,
body,token,exception. Do NOT cat/copy full ledger, trace TLS or monkeypatch launch.
No public receipt/admin route. Capture sanitized export as private operator
evidence under later QA scope, match UUID/type/browser opaque receipt, then obtain
independent visible group readback. HTTP200/mock alone is not live evidence.

## QC application deadline design and B1 remaining choice

Loopback-only127.0.0.1 default8787; nonloopback binds/peers rejected. Proxy only
exact /api/forms,/api/forms/status on QC origin. /health liveness stays private;
not evidence of bot/group/disk/capacity readiness. No public backend port,new
ingress,global listener edit,unit/service install or unrelated route modification.
Proxy must overwrite single validated client IP; QS_TRUST_LOOPBACK_PROXY=1 only
after verified. Default ignores forwarded headers (shared IP rate limit).
Disable API body/query/access/error detail logs and caching; no customer logs
from handler. Retain existing QC-only8KiB route body cap/no-store/upstream12s.

Absolute application policy starts when accept-loop admits loopback socket:
10s timer shuts down/closes socket even while bytes drip; request line+headers
aggregate16KiB,body8KiB,16 admitted sockets,no worker waiting queue,backlog16.
Provider wait<=8s AND remaining admission interval; no provider start after
budget expires, including slow reservation. Up to16 provider workers; timed-out
transport may continue but cannot mutate state or trigger retry. Slow disk or
uncancellable kernel calls may keep a bounded slot busy after socket closes;
not a hard real-time CPU/disk cancellation guarantee. Timer scheduling depends
on OS scheduling; test timing includes tolerance. Provider capacity exhaustion
fails before send. Up to16 timers+16HTTP+16provider threads plus main fits proposed
TasksMax64 for a single process, subject to deployment measurement.

These controls protect QC application resources downstream of trusted proxy.
They do NOT enforce an absolute public header/body deadline on shared Caddy
:443, before Host routing; HTTP2/3 streams there are unbounded by this timer.
Original frozen v1 demanded that protection; current shared listener has no
explicit<=10s bound per deployment report. This increment DOES NOT mark B1
resolved or waive that requirement. Independent review must assess this narrower
architecture and owner must choose acceptance of that explicit residual ingress
risk OR separately authorize shared-listener protection/compatible ingress design.
Backend cannot supply a public pre-Host deadline with QC route-only source code.
No owner question/release permission inferred from local test success.

## Capacity, TTL and rollback

One process; bounded16requests/16provider workers/16backlog,5IP/min+60global/min,
4096IP buckets,10000technical UUID entries;24h public outcomeTTL then unknown
tombstones retained. At capacity new503,no deletion/pruning/reuse. State JSON
whole-file fsync per event is for low-volume traffic, not a throughput guarantee.
Proposed256MiBRAM,20MiB private disk,1CPU share remain subject to reviewed host
capacity and service plan; do not install/assume supervisor limits from docs.
Health only liveness; monitor aggregate counts/capacity without PII/UUID logs.
Distributed abuse/shared ingress exhaustion remain explicit limitations.

New descriptor must bind exact frontend + this manifest + predeclared synthetic
configuration + chosen deadline decision. Independent review/release owners must
resolve B1 and secret/unit/route prerequisites before staging/activation. Rollback
only reviewed QC routes/code; preserve newest ledger/receipts. Never restore
historical shared Caddy wholesale or change course/Mono/Reader. No Git publication.
