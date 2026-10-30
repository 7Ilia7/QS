# Activation acceptance session — 30 October 2026

Reviewed V2 was adopted through PR #4. Initial main source
`3d36a3c0305500a5e57b4853da210c67f856ee47` passed Website CI run
`41111303024`; its exact artifact was independently downloaded and verified.
The restricted Linux transport and the main-only production environment are
installed. One-time bootstrap run `41114066361` passed all 27 HTTPS file checks
with unchanged private code, service processes and forms-state metadata.
`QS_AUTO_CD_READY=true` was enabled only after that verified bootstrap.

This documentation-only follow-up exercises ordinary merge → main CI →
automatic publication. It changes no site, application, workflow or transport
bytes. Actual automatic-release/rollback results and independent final QA are
recorded separately; this commit does not claim those pending checks passed.

# Implementation session — 30 October 2026

V2 correction handoff evt-owner-cb0d826b6dfae083291367c4: after independent V1
HOLD completed/released17, fixed real site/app root-directory and Git blob
provenance checks before artifact construction. Real clean-Git CLI fixtures
reproduce the old same-HEAD/external-bytes defect and now reject both absolute
and relative roots, while retaining nested checks. Product27/11 stays identical.

Direct owner steering selected automatic publication after merge to main.
V2 automatically consumes the successful trusted main CI's exact immutable
artifact, rejects stale/fork/PR/failure events and preserves a durable maximum
CI-run identity across manual rollback. There is a one-time no-switch baseline
bootstrap/enablement sequence; routine releases have no environment reviewer.
Generic skill core is unchanged; only its QS reference reflects this policy.
Exact V2 commit/freeze/actual tests and READY are in canonical packet
operations/deployment/cicd/20261030-v2. No remote effects in this correction.

The implementation notes below describe the historical V1 preparation.

LOCAL CI/CD candidate only. New handoff evt-owner-c6a0ec1755d58a1d75b5ea5d.
Canonical dirty checkout preserved; clean worktree branch
codex/website-release-cicd-20261030 adopts exact released27 public/11 private
files into site/app. No product/content/backend changes and no live deployment.

Implemented deterministic allowlist build, source/ZIP/tar integrity checks,
successful-main-CI selection, manual promotion/rollback with SHA compare-and-swap,
restricted forced-command receiver, metadata status/journal and public HTTPS
content checks. State/credential/ledger initialization is outside routine release.
Generic website-release skill and QS reference are separate.

Tests are observable local/temp-filesystem simulations; actual Actions runs,
environment configuration, deploy identity/key installation and production
promotion remain separate activation work after independent review. Initial
failed checks and corrections are preserved in the canonical implementation
packet operations/deployment/cicd/20261030-v1. Exact final source/skill digests,
commands and outcomes are in that packet's READY_FOR_QA/freeze/verification.
