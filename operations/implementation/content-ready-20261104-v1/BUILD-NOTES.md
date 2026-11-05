The existing public source policy permits JavaScript and rejects JSON files.
Owner-editable content therefore uses a small native deferred content-data.js
configuration, with a JSON-compatible object assigned to window.qsStudioContent.
The renderer reads fields and creates text nodes; it does not evaluate supplied
strings or inject supplied HTML. Missing configuration/schema retains safe slots.
The read-only audit parses the literal object without executing it.

No builder/receiver/CI policy was weakened or changed. The first local commit
652700ec1f0cf42de7416116961778cce41d797b failed public_type before producing a
build. That attempt is not PASS. The corrected final source/build is identified
only by the subsequent freeze.json and build-frontend manifest.
