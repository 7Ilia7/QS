# Callback estimate v1 — proposed integration contract

Handoff evt-owner-a91c48cf94ba5dde783e9862; parent evt-owner-5017b318316de1351132cc22.
Current8a803 main app/backend/server.py:34–57 rejects unknown payload fields.
Canonical backend follows frontend writer stop; web role does not edit app/.

Optional callback-only field:
```json
{"estimate":{"version":1,"master":"master","grams":100,"removal":false}}
```
Exact keys. version integer1 (not boolean), master enum master|olena, grams finite
positive JSON number (not boolean/string/NaN/Infinity), removal boolean. Unit grams;
decimals accepted. No artificial upper business limit in current calculator.
Half-open0<g<50,50<=g<100,100<=g<200,>=200.
Master3100/5300/7500/9700; Team Leader Олена4400/6600/8800/11000.
Removal adds1300 when true. Hair excluded. Backend derives amounts; no client
monetary fields/free text. Reject estimate on review. Absent estimate preserves
ordinary callback API; name/phone never contain hidden calculation data.

Safe compatibility: read-only same-origin GET /api/forms/capabilities returns
`{"estimate":{"version":1}}`. Only200/supportedversion enables estimate submit.
404/timeout/malformed/unsupported leaves attachment submit disabled. User may
explicitly uncheck attachment and send ordinary callback; no silent context drop.
Endpoint support is not delivery/health proof. No credentials.

Preserve qc-web/consent/8KiB/UUID/idempotency/rate-limit/status/retry/unknown locks.
Normalized estimate participates in fingerprint and durable record. Backend
formats authoritative work/removal/total/hair-excluded summary for Telegram.
Same UUID with changed estimate is not retry authority. Existing receipt/status
schema unchanged. No real send, BotAPI, spentUUID replay or runtime migration.

Frontend live summary follows edits/reset/invalid weights; Discuss opens/focuses
callback and optionally attaches current estimate without auto-submit. Busy/locked
request snapshot stays frozen while calculator changes. Explicit local mocked
GET/POST verifies adapter only. Backend implementation/review still pending.
