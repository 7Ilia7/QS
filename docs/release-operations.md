# QS publication — automatic after main merge

The owner's30Oct policy is automatic publication after merge to main. Edit
site/app in a branch, update the allowlist when needed, run checks/PR review/QA
and merge. Successful trusted main-push Website CI automatically publishes its
exact artifact/run/SHA. No second build, routine promotion button or environment
reviewer is required. PR/fork/failure/cancelled/non-main events cannot publish.
Generic skill defaults for other projects are unchanged.

Builder source roots must be actual checkout directories; declared source bytes
must match HEAD blobs. Root/nested symlinks, untracked declared source and hidden
non-HEAD bytes are rejected before artifact construction. Trusted CI artifact
ZIP/internal tar/manifest hashes bind the version. Deployment runner code comes
from trusted default main, never from the downloaded artifact.

One-time setup in activation.md keeps readiness false before adoption, installs
the limited transport/config/secrets/pin, bootstraps the byte-identical baseline
without a code switch, verifies HTTPS, then enables automatic CD once. It remains
enabled for ordinary releases. Existing protected-main checks/product QA apply.

The production queue does not kill an active switch or discard an older pending
event merely because a later event arrived. It does not assume commit ordering.
Selection and pre-mutation checks require current main SHA; client also prevents
automatic ancestry downgrade. Receiver CAS and atomic durable CI-run reservation
exclude stale/duplicate/out-of-order writes. This journal is separate from forms
data. Manual rollback preserves its maximum run number.

Backend readiness precedes UI activation. Only a changed private package restarts
qs-forms.service. HTTPS readback verifies every public file's TLS/status/bytes/
hash/MIME. Sanitized production-receipt includes selection, status, activation and
readback. This does not replace affected product UI/provider acceptance.

## Manual rollback

Website production → Run workflow on main: action `rollback`, previous installed
full source SHA, its successful main CI run ID and explicit current production
SHA. Target files must match that trusted artifact; the baseline alias is eligible.
Current forms state/HMAC/receipts are preserved. Old CI reruns cannot undo the
rollback; a newer merged commit/newer successful main CI publishes normally.

CI artifact retention is requested for90days, subject to repository policy. Do
not substitute/rebuild an expired artifact silently; deliberately revalidate an
older version in a recovery task. Installed files/receipts are not auto-pruned.

On lost/failed publication, inspect existing status/journal. SSH may have already
activated code. Do not retry mutation or reset data automatically. Interrupted
staging/backend/UI blocks further automatic switches until reconciled; explicit
rollback restores code while retaining the maximum run reservation. Failed
HTTPS readback after switching means code may be changed, not an unchanged site.

With the dedicated restricted key and verified known_hosts, send
`{"action":"status"}\n` to `ssh qs-deploy@165.245.223.138 qs-release`.
Only fixed JSON/tar protocol is available, no shell/SCP/SFTP. Status exposes safe
code/delivery identity/liveness, no environment/ledger contents.

Normal releases need no bot credential retrieval/rotation/provisioning, forms
state initialization, Caddy reload, real sends or historical special UUIDs.
Preserve course/Mono/unrelated Caddy and current private application state.
