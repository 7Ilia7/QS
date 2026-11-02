# Main landing implementation — 2 November 2026

Implementation handoff: evt-owner-0ee8cecb6e0b6dc9686f360c.
Parent: evt-owner-9b6c6cefcfbfe670618a1a69.
Canonical executor: qs-web-developer, chat 01a10ca1-a557-7931-b5a2-2e6decdd2cb0.
Owner brief: /Users/a1/.codex/visualizations/2026/10/05/01a10ca1-9e6d-7b13-b362-7fc1c3b99001/qs-landing-brief-20261102.md.

## Source and changes

A fresh remote clone was checked out on codex/main-landing-20261102 at main
c1703c655e0f65fa354e44c328b35d1de50439f3. Four public core files were independently
fetched by HTTPS and matched main byte for byte (see /Users/a1/.codex/visualizations/2026/10/05/01a10ca1-a557-7931-b5a2-2e6decdd2cb0/qs-main-landing-implementation-20261102-v1/live-baseline.json).
The dirty original QS working tree was preserved.

Only site/index.html, site/script.js, site/styles.css and site/forms.css changed
in the served payload. Existing approved studio, before/after and capsule media
are reused. The services now reproduce all ten owner photographs as accessible
text tables. Photo suffixes 3254–3263 belong to
/Users/a1/Downloads/photo_542511869264469<SUFFIX>_y.jpg. Originals were visually
inspected; phone/story overlays were not published. Literal LABEL spelling and
length categories 1–5 are preserved without invented centimeter definitions.
Four-hand source wording is retained with its unpriced gap explicitly disclosed.

The first screen introduces the studio; about, services/prices, genuine work,
work-only calculator and contact follow in that order. Calculator uses positive
grams and Master / team leader Олена; half-open brackets at 50/100/200, optional
removal 1300 and separate hair cost. Invalid inputs remove the quote and reset
the WhatsApp draft rather than retaining a stale calculation.

The map, callback and private review form occupy one aligned desktop grid, two
columns below 1100px, one column on mobile. Consent, privacy, field identities,
UUID/status/retry behavior and the Google Maps point/fallback are preserved.
forms.js, privacy.html, app/, release/allowlist.json, automation/ and .github/
are unchanged. No new public assets or dependencies.

## Initial scroll: observed facts and limit

Baseline local Chrome: fresh root y=0; contact anchor y=5398; another fresh root
y=0; no automatic focus() calls. Current forms.js only focuses on invalid submit
and explicit New request. There is no demonstrated startup-focus cause.
The reported bottom-opening issue was NOT reproduced in the fresh local context;
its original session/history cause remains UNKNOWN.

Defensive behavior now sets the top once on pageshow only for a new, hashless
navigation with no user interaction before load. Reload, history/BFCache,
intentional hashes and user scrolling before load retain native behavior.
There is no timer, hash removal or repeated scroll enforcement.

## Author verification

13 scenario groups passed in local real Chrome over HTTP at 127.0.0.1:8024:
fresh root/focus; section/media identity; both tariffs at 0.1,49,49.99,50,99,99.99,
100,199,199.99,200,250g with removal on/off; empty/zero/negative/non-number;
all 25 table rows/59 price cells; gallery/Escape; hash/reload/history; invalid
forms/consent/privacy; aligned desktop cards; stored unknown recovery (MOCKED
status GET); 320/390/768/1024 widths and keyboard menu; reachable mobile form
buttons; user scroll during delayed image load.

All POST and external-origin requests were aborted by the test harness. There
were ZERO POST attempts and zero page JS errors. Google iframe rendering was
therefore NOT tested, and its blank/error placeholder in screenshots is expected.
GET recovery response is mocked, not backend/delivery evidence. Local asset
check passes with 27 public files and no network calls. These are author checks,
not independent QA acceptance or deployment proof.

Evidence: author-checks.json, price-matrix.txt, screenshots/ here. The exact
source/build and payload hashes are in /Users/a1/.codex/visualizations/2026/10/05/01a10ca1-a557-7931-b5a2-2e6decdd2cb0/qs-main-landing-implementation-20261102-v1/freeze.json and
/Users/a1/.codex/visualizations/2026/10/05/01a10ca1-a557-7931-b5a2-2e6decdd2cb0/qs-main-landing-implementation-20261102-v1/build-candidate/release.json. These are generated after the candidate
commit, so the committed packet does not contain a self-referential commit SHA.

## Reproduce safely

Start: python3 -m http.server 8024 --bind 127.0.0.1 --directory site
Run author-check.mjs with Node and an existing Playwright/Chrome runtime, passing
an existing output directory. The harness is fixed to local port8024 and blocks
all POST and external resources. Do not substitute production or real fixture IDs.
Static assets: python3 automation/check_source.py.
Build: python3 automation/build.py --source-sha "$(git rev-parse HEAD)" --output NEW_DIR.

## Remaining workflow

Independent exact-build QA is PENDING with canonical qs-quality-reviewer /
qs-quality-review; coordinator must use the existing durable handoff and verify
delivery plus acceptance. No QA handoff was fabricated by this developer.
No real form submission, provider send, phone call, messaging flow, push, merge,
deployment, SSH, secret read or server state change occurred. Owner-approved
full build, reviewed PR/main, automatic deployment and live readback remain
required in the parent/release scope after QA. Local completion is not the
terminal result of that parent objective.
