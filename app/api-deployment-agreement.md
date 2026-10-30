# QC correction agreement — 2026-10-23

Public API unchanged:POST /api/forms, GET /api/forms/status, same JSON fields,
UUIDv4 + matching Idempotency-Key, opaque receipt_id only; no provider IDs,
target, receipt lookup/admin route or synthetic flag in browser API. Existing
limits8KiB/24h/provider8s/browser15s and no blind retry remain. No UI secret.

For later separately approved two-message QA, operator must predeclare exactly
one callback UUIDv4 and one review UUIDv4 in QS_SYNTHETIC_PAIRS JSON mapping
{UUID:"callback",UUID:"review"}. Frozen descriptor must bind these identities
before spending quota. Values chosen by release QA, not assigned/sent here.
UI QA uses those exact request IDs through an independently reviewed fixture
mechanism; never replace an uncertain ID. No synthetic control accepted from
public body. Predeclaration is immutable within initialized private state.

Only matching two requests may retain sanitized Bot API receipt metadata, inside
private durable outcomes.json records; not in public manifest, logs or status.
Fields:request_id/type/ok/message_id/target/timestamp/receipt_id only. Receipt
and delivered outcome commit atomically to one0600 state file, not two loosely
coupled logs. Ordinary customers retain only previous opaque technical state.
Receipt loss/corruption, deadline or crash cannot enable resend or success.
No actual UUID pairs/credential/live sends provisioned in this local child.

B1 replacement is explicit application boundary design for review: absolute
10s from accepted loopback socket through headers/body/application response;
header cap16KiB,16 admitted sockets, bounded backlog16, no waiting worker queue,
non-loopback peer rejected, proxy overwrites validated single XFF. Health remains
private. A timer closes admitted sockets even if bytes drip continuously.
No provider send starts after application admission deadline; late outcome is
unknown, no automatic retry. Deployment must verify exact trusted proxy route,
privacy, upstream timeout and new application's behavior without global edits.

This DOES NOT supply public :443 absolute header/body deadlines before Host
routing. Existing shared Caddy ingress retains its current behavior; HTTP2/3
streams/connections and resource occupancy there are outside application bounds.
Thus frozen v1 public ingress<=10s precondition is NOT satisfied by moving a
timer inward. B1 remains a release decision: accept this expressly narrower
QC application-boundary design through independent review/owner decision, OR
separately authorize shared-listener protection/new suitable ingress design.
No silent waiver, shared config edit or claim of absent public protection.
