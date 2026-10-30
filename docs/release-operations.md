# Normal website publication

Edit `site/` and, when needed, the private `app/` source in a reviewed branch.
Update `release/allowlist.json` when adding/removing files. Production config,
credentials and runtime data are outside those trees. Run the local checks,
commit and PR; automatic CI tests and builds the explicit artifact. Review the
actual GitHub result, then merge. PR/fork artifacts cannot be selected for CD.

In GitHub Actions choose **Website production → Run workflow** on main:

- action `promote`;
- `source_sha`: the full successful main-push CI SHA;
- `ci_run_id`: that exact successful Website CI run ID;
- `expected_current`: the full production SHA from its last verified receipt
  or the restricted status endpoint.

The protected environment holds the production secret. The job verifies trusted
run identity, main ancestry, artifact ID and ZIP digest, then the internal tar
allowlist/hashes. The receiver compares current SHA before writing, stages new
immutable code, makes backend ready before switching the public pointer and
checks shared metadata. The client checks every public file by TLS/status/
bytes/hash/MIME. It saves a sanitized `production-receipt-<run>-<attempt>`.
Success is activated/read-back code, not automatic real form or external-provider
acceptance for arbitrary feature changes; route affected product QA separately.

Rollback uses the same manual button with action `rollback`, the selected
previously locally activated SHA/its successful CI run and the current SHA.
The baseline source alias is also eligible. Both public/private target files
must still match that artifact; no in-place overwrite or old state restore.
CI artifacts are requested for90-day retention, subject to repository policy;
an expired artifact cannot be silently substituted/rebuilt. Revalidate an older
version in an explicitly selected recovery task if its trusted artifact is gone.
Installed code/receipts are not automatically pruned.

On failure/lost SSH result, stop and inspect the existing status/operation
journal. Do not rerun the workflow or reset state automatically. The journal
records staging, backend switch, UI switch and local verification phases. A
failed backend readiness check leaves the public pointer unchanged; an explicit
rollback can restore the prior code while preserving the newest state. If public
HTTPS readback fails after switching, production may already be changed: use
the recorded current SHA and choose a deliberate rollback, not a blind retry.

Restricted status request (using only the dedicated deployment key and verified
known_hosts, never the old root key): send `{"action":"status"}\n` to
`ssh qs-deploy@165.245.223.138 qs-release`. The forced endpoint ignores caller
command text and accepts only its bounded JSON/tar protocol; no SCP/SFTP shell.

No normal release requires Telegram token retrieval/rotation/provisioning,
state initialization, Caddy reload, real submissions, customer messages or
special historical test UUIDs. Preserve the existing forms data and shared sites.
