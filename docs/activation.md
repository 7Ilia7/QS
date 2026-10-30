# One-time remote activation — candidate, NOT EXECUTED

Owner scope currently allows local engineering plus bounded read-only GitHub/SSH.
The steps below require independently reviewed exact files and a separate narrow
activation assignment. Existing approvals within that assignment suffice; no
new Telegram credential or form test is needed.

## Verified preparation facts

GitHub7Ilia7/QS is public; main6a296d2bdae6a05e2b104df90e27a9ceab1272ae,
unprotected; authenticated7Ilia7 has admin. Actions enabled, no workflows or
environments. Live public/private code matches frozen27/11 manifests; normal
qs-forms service active/restarts0. Neither qs-deploy nor /usr/local/sbin/qs-release
exists. These are30Oct observations, not permanent assumptions; refresh at activation.

## Exact activation changes

1. Publish only the reviewed clean candidate branch, preserving the dirty canonical
   checkout. Open/review/merge its source adoption and workflows into main; no
   git-add-all from the old checkout. A PR CI run checks the candidate, then a
   successful main-push CI run produces `website-<full-main-SHA>`.
2. Configure repository branch/ruleset protection for main with the actual
   `Website CI / verify-build` check and review policy selected by the owner.
   Configure environment `qs-production`: main deployment branch policy, required
   reviewer7Ilia7 (or an owner-selected reviewer), no implicit unprotected environment.
   A sole owner must choose whether self-review is permitted; prevent-self-review
   with only that same owner would make self-triggered runs unapprovable. Do not
   bypass a waiting protection rule to compensate.
3. Create ONE dedicated application transport identity/key under the activation
   scope. Never reuse the existing root SSH key as a GitHub secret. Server system
   account `qs-deploy` has a locked password and /bin/sh only to support sshd's
   forced-command execution; it receives no unrestricted shell/key. Home and
   .ssh are root-owned0755; authorized_keys root0644. The sole key line is:

   `restrict,command="/usr/bin/sudo -n /usr/local/sbin/qs-release" <PUBLIC_DEPLOY_KEY>`

   Key creation/delivery belongs to protected activation; values do not enter the
   repository, skill, logs or chat. Store its private half only in environment
   secret `QS_DEPLOY_SSH_KEY`.
4. Install the independently reviewed `automation/receiver.py` and
   `automation/release_lib.py` root:root0644 in `/usr/local/lib/qs-release/`
   (root0755). Install `automation/qs-release` root0755 at
   `/usr/local/sbin/qs-release`. Install only the exact sudoers template after
   `visudo -cf` validation. It permits zero-argument invocation of that endpoint,
   not arbitrary sudo, systemctl, shell, SCP or SFTP commands.
5. Install `/etc/qs-release/` root0700 and `config.json` root0600; create
   `/var/lib/qs-release/` root0700 for the deployment lock/journal/temp files.
   Generate config locally with `automation/activation_config.py` from the FIRST
   reviewed successful main CI's `release.json`. Its source SHA becomes the
   baseline alias for the already published qc-20261030-existing-v1 paths.
   Before installation, verify EVERY27/11 file against that manifest on the
   existing baseline paths and confirm current pointers/unit/shared identity.
   If the first approved main build's product bytes differ, STOP: it cannot be
   labelled as already deployed. Separate the byte-identical source adoption
   from subsequent site changes. The alias enables initial rollback without
   copying or redeploying the baseline or inventing a source SHA.
6. Set environment variable `QS_KNOWN_HOSTS` to the verified165.245.223.138 host
   public-key line, obtained from the trusted existing pin/out-of-band check.
   Do not establish trust by blindly accepting ssh-keyscan output. No host-key
   bypass, DNS/firewall/listener/Caddy change is required.
7. Use the restricted key to request `{"action":"status"}` on stdin. Confirm
   baseline SHA, exact code match and private liveness; check negative forced
   command/invalid request cannot obtain a shell or write outside the endpoint.
   Record installed helper/config hashes and actual environment/secret NAME
   presence, never secret values. Run the first approved production dispatch
   against the baseline SHA: `already_current_verified` plus full HTTPS readback
   validates delivery integration without switching byte-identical code.

Later promotions only use that transport. The receiver does not read/provision
the credential, initialize/reset the forms state, restore a ledger, edit Caddy,
change course/Mono, create resources or make Bot API calls. A changed backend
uses only `systemctl restart qs-forms.service`; static-only promotion has no
restart. Backend restarts can leave an in-flight request ambiguous; the existing
durable handler reconciles it without resending. Schema/data migrations are not
part of this code-only mechanism and require a compatible release plan.

## Activation readback

Retain actual PR/main CI IDs, selected source SHA/artifact ID/digest, configured
environment/protection metadata, restricted transport tests, receiver operation
receipt,27 HTTPS content results, private loopback status and unchanged shared
service/configuration metadata. Local YAML/actionlint/tests do not prove any of
these remote outcomes. Both old real form fixtures are exhausted; do not submit
them again or reset the ledger/HMAC. Independent review routes the exact local
candidate before this activation, with no new generic role/runtime policy.
