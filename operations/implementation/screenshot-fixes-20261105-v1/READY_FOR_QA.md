# READY_FOR_QA — five approved screenshot groups, LOCAL only

Web handoff evt-owner-e3a0a8e3f89015fafa9d09fe; parent evt-owner-70d4121acdffa429efec6494.
Executor qs-web-developer /01a10ca1-a557-7931-b5a2-2e6decdd2cb0.
Owner approved five-group brief including portfolio interpretation.
Source base095e1e345db69eba48cb3fd939e6c71d8a1a4f10, preserving ALL prior
content-ready, portrait fallback and private estimate backend enhancements.

Branch codex/qs-screenshot-fixes-20261105; source /Users/a1/.codex/visualizations/2026/10/05/01a10ca1-a557-7931-b5a2-2e6decdd2cb0/qs-screenshot-fixes-20261105-v1/worktree.
A separate descendant clone preserves the old frozen095e archive and its8047
owner preview. This is deliberate isolation, not a reset to old main.
Exact final commit/source/build39/private11equivalence/payload/archive/HTTP:
/Users/a1/.codex/visualizations/2026/10/05/01a10ca1-a557-7931-b5a2-2e6decdd2cb0/qs-screenshot-fixes-20261105-v1/freeze.json and build-combined/release.json / SHA256SUMS.

## Implemented approved groups
1. Hero: identical gold CTA component, equal grid-row heights; consultation label
   Записатися на безкоштовну консультацію. Separate free-consultation line,
   tiny hero facts, photo caption/English decoration and lower decorative strip
   removed. Image alt, branding, meaningful intro and navigation remain.
2. Services: one-line wide heading; natural mobile wrap. Right intro and lower
   length/range explanatory note removed; all cards and25price rows/59values retained.
3. Portfolio: one-line wide heading; adjacent case/capsule cards equal heights
   at1440/1024, normal stacked mobile. Original3-photo gallery is an explicit
   carousel with previous/next buttons, status, keyboard arrows/Home/End, native
   horizontal touch scrolling/scroll-snap and original image lightbox.
   Existing comparator and honest future-content slots remain unchanged.
4. Videos: details open initially, all6native source URLs assigned immediately,
   preload metadata. No autoplay attribute or initplay() call. Actual metadata
   requests observed before scrolling/user interaction; playback begins only on
   explicit native Play. Initial-failure retry prepares media without playing.
   Removed contradictory click-to-load text and initial load buttons.
5. Master select: appearance:none with a single CSS chevron inset18+px from edge,
   reserved40–44px padding. Native select retained;320px inputs stack for legibility.

Only public payload changes: site/index.html,site/script.js,site/styles.css.
No new imagery/dependencies/allowlist/CI/private API/forms/content source changes.
Exact static invariants: price table markup; calc/early JS; callback/mobile/content
and portrait helper JS; complete private-review commented body are unchanged.
No fake content; SEO draft noindex/robots/backlog retained. Night Luxury preserved.

## Author evidence
Eight focused REAL LOCAL UI/HTTP groups PASS at1440/1024/390/320. Hero heights/
style/copy, headings, equal cards, no page overflow, carousel button/keyboard/
native horizontal wheel input in touch-enabled contexts, lightbox, select option
change, all6metadata-ready while paused/currentTime0/initPlayCalls0, initial404/
retry without playing, actual native Play => playing/currentTime>0.
Physical-device finger swipe/Safari/hardware safe-area not tested; native overflow
and emulated widths are bounded evidence, not physical-device acceptance.
One harness attempt clicked the native seek bar instead of Play; corrected to the
observed native Play position. No product autoplay workaround was introduced.
No POST attempts/real sends. See author-results.json,media-http.json,invariants.json
and screenshots/. Full historical calc/context/private backend suite not repeated
because implementation bytes are identical; independent affected QA still required.

Media HTTP:18source-byte-equal range checks across6MP4s including head/open-ended/
suffix; invalid requests416. Range replies at most512KiB. Existing six full assets
total33,600,596bytes; preload=metadata is a browser resource hint, not a claim of
complete eager download or guaranteed transfer budget across browsers. The browser
may make additional range requests for metadata, seeking or explicit playback.

## Working preview
http://127.0.0.1:8048/__local_demo, PID38116, loopback8048.
Prominent LOCAL DEMO/no-delivery wrapper. Same actual private App + mock sender,
owned temporary synthetic state, no credentials/real transport, outbound socket
block and self-only CSP. New preview.py adds only correct bounded public-media
Range responses so approved local media are not blocked by the wrapper.
Public content and API mock work; app/private source paths are not served.
Synthetic data only; no real submissions.
Start from source root: python3 -B operations/implementation/screenshot-fixes-20261105-v1/preview.py --port 8048
Stop ONLY owned preview: kill 38116
Keep server running for owner/reviewer. Previous8044/8046/8047 and owner tabs
were not restarted, controlled or replaced.

## Independent next stage / authority
Canonical qs-quality-reviewer /qs-quality-review should review exact new bytes:
all five approved groups at wide/mobile, carousel focus/touch behavior, comparator/
capsule heights, video initial metadata/paused/retry/nativePlay and mediaRange/CSP,
master arrow and nearby booking/portrait/content/privacy/indexing regression.
Actual new handoff/delivery/acceptance PENDING parent. Author PASS is not final QA.
All11private backend rows must match095e in freeze; combined build is local, not
a publication or full external-delivery acceptance. Owner screenshot-change scope
is approved; release remains LOCAL only with no push/PR/main/deploy/SSH/server/
Google/secrets/real messaging/form/BotAPI effects. Stop writer after freeze.
