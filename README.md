# QS website source and delivery

This branch adopts the exact published `qc-20261030-existing-v1` source into
`site/` (27 public files) and `app/` (11 private package files). The former Git
root snapshot was not the published version. `release/import-provenance.json`
records the byte-preserved source; `release/allowlist.json` defines build members.
Business content, styles, features and backend implementation are unchanged.

Local static preview: `python3 -m http.server --directory site 8000`.
Checks: `python3 -B automation/check_source.py`, `node --check site/script.js`,
`node --check site/forms.js`, `python3 -B -m unittest discover -s tests -v`.
Run the existing backend suite from `app/backend`:
`python3 -B -m unittest discover -s . -p 'test_*.py' -v`.

CI runs on PRs/branch pushes, without production secrets, then builds an explicit
allowlist artifact. Owner-selected QS policy: successful trusted main-push CI
automatically publishes its exact artifact, without a per-release reviewer.
Rollback remains manual. Current-main, durable CI-run ordering, expected-current
comparison and HTTPS content readback protect production. One-time bootstrap
registers the already published source before auto-CD is enabled.

See [activation](docs/activation.md) for the separately reviewed one-time setup
and [release operations](docs/release-operations.md) for normal publication.
Local workflow files are not evidence of a remote CI run or active CD.

The reusable `website-release` Codex skill has a generic core and a separate QS
reference; it is not a runtime role or an extra credential provisioning process.
