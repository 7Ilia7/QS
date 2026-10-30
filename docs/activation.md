# One-time QS auto-CD activation — NOT EXECUTED

The owner chose automatic publication after merge to main on30Oct. Routine
releases must not wait for an environment reviewer/conversational approval.
This LOCAL candidate still requires independent exact-file review followed by
the separately authorized one-time remote setup below; no setup was executed.

Preparation observations: GitHub7Ilia7/QS public/admin7Ilia7, defaultmain at
6a296d2bdae6a05e2b104df90e27a9ceab1272ae, unprotected, Actions enabled,
workflows0/environments0. Live27/11 code matchesqc-20261030-existing-v1,
forms service active/restarts0. qs-deploy and receiver absent. Refresh these
bounded facts in the activation assignment, not by reading secrets/state.

## Ordered bootstrap, before routine automation

1. BEFORE publishing/merging the workflows, set/confirm repository variable
   `QS_AUTO_CD_READY` unset/false. Job and Python event policy skip automatic
   operations until this one-time readiness is enabled. Do not merge while an
   unknown preexisting true flag could race missing transport/config/secrets.
2. Publish only the independently reviewed clean candidate branch, review/merge
   source adoption/workflows into main and retain the actual successful main CI
   run/SHA/artifact ID/digest. Do not publish the canonical dirty directory.
   The initial workflow_run safely skips while readiness is false.
3. Protect main with the actual returned Website CI check context and PR/check
   policy; do not invent a workflow/job context string. Configure environment
   `qs-production` for main only, with NO required reviewers, wait timers or
   per-release manual gate. Normal branch review/QA still applies; its approval
   count follows the owner's project policy, not a new mandatory human gate.
4. Create the dedicated application transport account/key under the activation
   scope. Do not reuse the existing broad root SSH key as a GitHub secret. System
   user `qs-deploy` has a locked password and /bin/sh only for sshd forced-command
   execution. Home `/var/lib/qs-deploy` and .ssh are root-owned0755, authorized_keys
   root0644. The sole key line is:

   `restrict,command="/usr/bin/sudo -n /usr/local/sbin/qs-release" <PUBLIC_DEPLOY_KEY>`

   Key values stay in protected activation handling, never repo/skill/logs/chat.
   Store only its private half in environment secret `QS_DEPLOY_SSH_KEY`.
5. Install reviewed `automation/receiver.py`, `release_lib.py` and
   `delivery_policy.py` root0644 in `/usr/local/lib/qs-release/` root0755.
   Install reviewed wrapper `automation/qs-release` root0755 as
   `/usr/local/sbin/qs-release`. Validate exact `automation/qs-release.sudoers`
   with `visudo -cf` and install root0440: only zero-argument endpoint invocation,
   no arbitrary sudo/systemctl/shell/SCP/SFTP. Wrapper uses absolute Python `-I`.
6. Create `/etc/qs-release/` root0700, config.json root0600 and
   `/var/lib/qs-release/` root0700 for lock/journal/temp files. Generate nonsecret
   config with reviewed activation_config.py from the FIRST successful reviewed
   main CI's release.json. Its full source SHA aliases the already deployed
   qc-20261030-existing-v1 public/private paths. Verify EVERY27/11 file against
   that manifest on the baseline paths before installation. If bytes differ,
   STOP: do not label a changed product as already deployed. Separate identical
   source adoption from later site feature changes. Confirm current unit/shared
   identity; the baseline mapping must not be a guessed Git SHA.
7. Set environment variable `QS_KNOWN_HOSTS` to the verified165.245.223.138 public
   host-key line from the existing trusted pin/out-of-band check; do not establish
   trust by blindly accepting ssh-keyscan output. Install environment secret NAME
   QS_DEPLOY_SSH_KEY via protected handling, never displaying its value.
8. Test the restricted endpoint's `{"action":"status"}` and negative command/
   invalid request boundaries. Retain installed helper/config hashes, current
   code/health and environment/secret NAME presence, not secret values. With
   readiness still false, dispatch ONE `bootstrap` using that initial successful
   main CI source SHA/run. Require `bootstrap_verified`, unchanged code pointers/
   service and full HTTPS content readback. It registers CI ordering metadata in
   the deployment journal, not the forms ledger. No provider call or form send.
9. Recheck main still equals that exact bootstrapped SHA. Only after verified
   transport/config/key/pin/secret/status/HTTPS bootstrap, set repository variable
   `QS_AUTO_CD_READY=true` ONCE. Every later merged main push uses CI→automatic CD;
   no recurring reviewer or enablement. If main advanced, stop/reconcile the exact
   reviewed baseline mapping before enablement. Lost bootstrap outcome means
   inspect existing status/journal/public bytes, not blindly repeat registration.

Normal receiver actions never read/provision credential values, initialize/reset
forms state, restore ledger/HMAC, edit Caddy, touch course/Mono or send Bot API
requests. Only changed private code restarts the existing qs-forms.service;
static-only publication does not. Backend restarts may leave an in-flight
request ambiguous; durable reconciliation never automatically resends it.
Schema/data migrations need a compatible application plan outside this code switch.

## Ordering and actual acceptance

Automatic selection binds exact successful trusted main-push CI/run/SHA/ZIP
digest/internal allowlist, without rebuilding. A serialized non-cancelling
production job queue retains pending events (`queue: max`); queue order itself
is not trusted. Latest-main checks, ancestry/CAS and a durable maximum CI run
reservation prevent stale/duplicate/out-of-order publication. Manual rollback
keeps the maximum. Interrupted phases require reconciliation; deleting/recreating
the CI workflow identity requires reviewed deployment-metadata maintenance,
never a forms-state reset. The queue has GitHub's documented admission limit.

Retain actual source/CI/artifact IDs/digests, branch/environment configuration,
restricted transport tests, bootstrap/automatic/rollback receipts,27 HTTPS
hash/size/MIME/TLS results and unchanged shared metadata. Local tests do not prove
Linux/GitHub execution. Existing real form quotas are exhausted; never replay.

Primary references: [workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run),
[production queue/concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
[environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
Actionlint1.7.12 predates the documented queue key. Retain its raw diagnostic;
the remaining syntax can be checked with only that unsupported-key diagnostic
excluded. Actual GitHub workflow acceptance remains part of remote activation.
