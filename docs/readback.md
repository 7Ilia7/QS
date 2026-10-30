# Read-only recovery of a confirmed release — V3 LOCAL candidate

P2 `PIPELINE-POSTSWITCH-DNS` was observed in actual runs `41115014388` and
`41115818349`: the receiver confirmed a code switch, then the runner failed
HTTPS DNS resolution. Preserve those failed runs and the original receipts.
This candidate has not been pushed, run by GitHub or installed remotely.

## Bounded public checks

Only an actual `socket.gaierror(EAI_AGAIN)`, including nested `URLError.reason`,
retries the same anonymous GET: at most three attempts, with 1s then 3s backoff.
Permanent DNS, certificate errors, timeout/other network errors, HTTP status,
redirect, MIME, size or hash failures do not retry and never become PASS.
Default CA/hostname validation and the fixed HTTPS origin remain unchanged.

Scheduling budgets are 90s per resource and 600s for the complete readback;
each open uses at most 25s or the remaining budget. Deadlines are checked before
attempts/backoff and before/after each `HTTPResponse.read1`. No result returned
after a checked deadline is accepted. An already-running OS resolver/I/O can
outlast a scheduling deadline; the process cannot preempt libc DNS. The existing
15-minute job timeout remains the outer hard bound. No new resolver/DNS override
or TLS bypass is introduced. Retry improves the demonstrated symptom, not a
claim that its upstream root cause is solved.

The client writes `activated_receiver_verified_public_readback_pending` with
the validated receiver receipt **before** starting public GETs. On readback
failure it retains that phase and an error classification. No SSH mutation,
bootstrap or complete deployment job is retried.

## Verification-only resume, after reviewed activation of this candidate

Choose the exact currently installed source SHA and its successful trusted
main-push Website CI run; do not rerun either failed deployment job. The proposed
production dispatch action is `verify`, with all three exact inputs:

```
action=verify
source_sha=<full currently installed SHA>
ci_run_id=<successful main push CI run for that SHA>
expected_current=<the same full SHA>
```

The selector requires the fixed repository/main dispatch, successful same-repo
main-push CI, exact SHA/artifact, verified provider ZIP digest/internal manifest
and main ancestry. A currently installed older main SHA may be checked. A new
`operation=verify_only` selection cannot enter the mutating client path; it has
no deployment delivery action. Existing automatic/rollback selection is retained.

The explicit local entry point for that selector-produced directory is:

```bash
python automation/deploy.py --verify-only --expected-source-sha <same-full-SHA> \
  --artifact out/selected --report out/verification-receipt
```

It sends exactly two `{"action":"status"}` requests to the existing fixed
restricted endpoint, with public GETs in between. Both statuses must match the
explicit SHA, manifest payload/code, health, fixed public/private paths, terminal
receiver phase, and selected CI workflow/run identity. They must be identical
before/after, including journal and maximum automatic run. It rechecks current
status even after GET failure. Missing/unknown status, incomplete phase, changed
SHA/paths/journal/watermark, or unhealthy code refuses PASS without a mutation.

The mode does not import/invoke the receiver mutation handler, change pointers,
initialize state, touch the forms ledger, update a watermark or restart services.
It produces a **new** separate verification receipt, preserving original failed
job history. `PASS_verification_only` means this new check passed; it does not
rewrite an old failure into a green run. Failed rechecks remain explicit/pending.

V3 changes only runner-side client/selector/workflow/tests/docs and the QS skill
reference. Installed receiver/release_lib/delivery_policy bytes remain compatible
and unchanged; no root helper reinstall is required by this candidate.
Site27/app11, AUTO-after-main, branch/environment controls, existing keys and
credentials/state remain unchanged. Independent source retest and a separately
reviewed actual runner verification/automatic acceptance are still required.
