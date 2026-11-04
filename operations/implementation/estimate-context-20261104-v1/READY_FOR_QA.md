# READY_FOR_QA — combined estimate context, LOCAL only

- Request qs-estimate-context-backend-20261104-v1; exact handoff evt-owner-259bf247eee6716383727b21;
  parent evt-owner-5017b318316de1351132cc22; canonical backend executor thread01a10ca1-b2f0-7501-88ce-d633f3774485.
- Exact immutable commit/archive/payload, preview PID and HTTP evidence:
  /Users/a1/.codex/visualizations/2026/10/05/01a10ca1-b2f0-7501-88ce-d633f3774485/qs-estimate-context-backend-20261104-v1/freeze.json.
  That file is generated after commit/full build; no source SHA invented in advance.
- Source worktree is sibling worktree/ under that same artifact directory;
  branch codex/qs-estimate-context-20261104, base frozen frontendb5a23f98fe897af940f25d9069491a818386a379.
  Local clone, no original worktree/canonical dirty source modified.28public bytes
  identical to frontend; full combined39member build remains28public/11private.
- Product contract: existing frontend callback-estimate-contract.md accepted
  without schema change. Optional estimate onlycallback: exactkeys version(int1),
  master(master|olena),grams(positive finite JSONnumber,booleans/strings rejected),
  removal(boolean). No client prices/unknown fields. Exact half-open50/100/200,
  Master3100/5300/7500/9700,Олена4400/6600/8800/11000; optional removal1300; hair extra.
- Amounts computed in server, escaped authoritative notification text. Machine
  estimate stored in private technical reservation and canonical HMAC fingerprint.
  Equivalent100/100.0 matches; changed master/grams/removal on sameUUID gives409.
  Ordinary callback unchanged; estimate on review rejected. GET capabilities
  {estimate:{version:1}} read-only and same-origin, no health/delivery inference.
  Status/receipts contain no estimate/customer/provider details. Existing8KiB,
  rate/deadline/concurrency/TTL/crash/unknown/no-blind-retry semantics preserved.
- Change surface: app/backend/server.py, app/README.md, app/Readmde.md;
  tests/test_estimate.py and local implementation docs/tools. No public assets/UI,
  allowlist,CI,workflow,environment,secret,price/contact/map edits.
- Owned stable integrated preview http://127.0.0.1:8046/__local_demo, PID23912.
  Serve unchanged source public bytes from /index.html within persistent labelled
  demo wrapper; actual modified App handles same-origin APIs. Sender is localmock,
  NOT Telegram; no credentials read, external socket connections blocked. All
  browser external resources blocked by preview CSP (Google map intentionally
  unavailable; not a product defect claim). No request/body/PII logs.
- Start: python3 -B operations/implementation/estimate-context-20261104-v1/preview.py --port8046
  (use `--port 8046` as separate arguments). Stop ONLY ownedpreview: kill23912.
  Temp state removed on stop; preview restart creates NEW DEMO ledger, not production
  recovery procedure. Keep this preview alive for owner. Originalstatic8044/PID65706
  stays unchanged; no borrowed process killed.8045 start failed Address already
  in use; no listener created there. No permissions denial bypass.
- Private source/state paths404; allowlist-only static handler, no directory index,
  no external proxy/forward, no publichealth/admin/receipt API. Wrapper only is
  demo UI from local tool, not changed product bytes or part of release payload.
- Author evidence:6 semantic test groups PASS,32 existing backend tests PASS,
  REAL LOCAL HTTP/MOCK notification check author-http.json:28hashes,7private404,
  capabilities200,estimate/plain200,duplicate/status200,context409,clientamount422.
  This is author verification, not independent UI/product acceptance/live delivery.
- Reproduce semantic tests: python3 -B -m unittest discover -s tests -p test_estimate.py -v.
  Existing regression from app/backend: python3 -B -m unittest -v test_server test_correction.
  HTTPcheck: python3 -B operations/implementation/estimate-context-20261104-v1/author_http.py.
  It creates NEW owned synthetic UUIDs in demo state only, never replays old IDs.
- Allowed independentQA: read-only localUI/GET, new owned synthetic mock-only
  callback requests to8046, validation/idempotency/status/unknown behavior,
  calculator-to-form at desktop/mobile320/390/768/1440, keyboard focus/consent and
  frozen submitted context while editing calculator. Test master/decimal boundaries,
  invalid versions/types/extra monetary fields, review rejection and plainfallback.
  Unknown/failure transport injection only in separate owned local test instance,
  not monkeypatching a deployed service. No real notification quota:0/0.
- Forbidden: secrets, real BotAPI/Reader sends, spent UUID replay, production
  requests/submissions, call/messagingactivation,SSH,server,Google,analytics,
  push/PR/merge/main/deploy, unrelatedprocesses/settings. Demo accepts onlysynthetic
  contact fixture+380000000001/LOCAL MOCK ONLY; no actual customer data.
- Known limits/PENDING: independent combinedQA, ownervisualapproval, actual browser
  native-mobile keyboard/safearea, externalmap and live capability route/provider
  deployment. Current deployed backend is NOT inferred to support estimate; future
  reviewed release must route GET /api/forms/capabilities as well as existing API.
  No proxyconfig edits in this task. Draftnoindex/robots remains intentional and
  must not be mistaken for productionSEO approval.
- CanonicalQA target qs-quality-reviewer / qs-quality-review /01a10ca1-abff-74b1-9c13-15bc6634663f.
  Actual combinedhandoff/delivery/acceptance PENDING coordinator; separate frontend
  QA55af100a does not imply this new backend has independent signoff.
- Writer stops/freezes before completion and independentQA; preview runtime may
  remain for owner, source cannot change during review. Buildidentity changes
  invalidate affectedsignoff; fixes require new exactretest/affectedregression.

| Scenario / tier | Expected and actual author result | Status / limitation |
|---|---|---|
| Both masters, decimalneighbors and50/100/200/removal, UNIT/MOCKED | Original exact work/extra/total values | PASS; no live pricing claim |
| Invalid schema/clientprices/review estimate, UNIT/MOCKED |422,zero sendercalls | PASS |
| UUID equivalent/change/restart/statusprivacy, UNIT/MOCKED | Replay same,change409,noestimateinstatus,noresend | PASS |
| Existing32mockedbackendregression | Deadlines/crash/rate/receipt/duplicate unchanged | PASS; no destination proof |
| CombinedHTTP8046, REALLOCAL/MOCK notification |28exactpublic bytes,private404,capability/estimate/plain/status | PASS; locally simulated delivery only |
| Independent combinedUI/API | Canonical reviewer exactnewfreeze | PENDING |
| Owner approval / publication | Explicit owner choice for these exactbytes | PENDING / NOT RUN |
