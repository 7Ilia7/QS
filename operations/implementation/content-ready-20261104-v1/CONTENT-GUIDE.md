# Content insertion guide — local owner preview

Edit the plain object in site/content-data.js (schema qs.content.v1). Keep its
window.qsStudioContent assignment wrapper and JSON-compatible quoted keys/values. It contains no credentials and is
the only source for the new cases/team/reviews/FAQ. Keep mode owner-preview until
the exact new content/layout has owner approval. Ready means supplied material,
not automatic release authority. Night Luxury identity and authoritative prices
remain in existing markup/calculator; content editing must not change tariffs.

## Cases
Each item: id, status draft|ready, title (<=120chars), procedure (<=160),
grams (positive finite number or null), master master|olena|null,
before/after photo objects or null, framing contain.
A photo: src relative img/... path; width/height positive integer; meaningful alt.
Use only approved real matched before/after of the SAME client/procedure, same
orientation/camera distance/angle, lighting and canvas dimensions. Do not crop two
unidentified photos into a new pair or split the existing composite without proof.
Recommended pair: 960x1200 (4:5), or a matched square; same dimensions both sides.
WebP/AVIF preferred, each about50–150KiB, ideally <=200KiB. Keep original unedited
sources privately with consent/provenance. No synthetic clients/results.
Both images share one contain frame; resizing the divider never changes scale.
Missing/mismatched metadata/images/status stay an explicit neutral preview slot.
Runtime also catches broken files/aspect mismatch and disables invalid comparison.
The existing authentic gallery remains independent of new case attribution.
Capsule closeup currently reuses approved capsules480/960 with its own lightbox.

## Team
Each: id olena|master|stable-id; status draft|ready; name, role, portrait (same photo
object), specialties array (<=5 concise items), bio (<=600chars).
Only current fact defaults are Team Leader Олена and the Master pricing role.
Unknown names, real specialties, bio and portrait stay empty; no stock faces,
invented experience, certificates, awards or claims. Portrait suggested640x800
(4:5), WebP/AVIF, <=150KiB; keep face in central safe crop. Verify consent/name
attribution and provide real alt text. Draft placeholders are not employee photos.

## Reviews
Default array is EMPTY. Each ready entry requires author, quote (<=1200chars),
source_url (https original), status ready. Use the exact genuine quotation with
permission and an attributable original source; no paraphrased quote disguised as
verbatim, ratings, fake stars, invented clients or duplicate reposts. Remove
personal details not approved for display. No Review/AggregateRating JSON-LD is
generated. Private review form stays in its original complete HTML comment.
Invalid/missing/source-less reviews are not rendered as testimonials.

## FAQ
Each: id, question (<=180chars), answer (<=1600), status draft|ready|existing-facts.
Five slots cover grams, duration, correction, care, inclusions. Existing-facts
answers use current published price/general facts only. Studio-specific duration,
care/schedules/medical answers stay draft until supplied/approved. An empty answer
shows an explicit awaiting-content note. No invented timings or contraindications.

## Files / security / publication
Images are local relative img/[letters,digits,slash,underscore,hyphen].extension;
extensions webp,avif,jpg,jpeg,png. No remote image URLs, query strings, traversal,
inline HTML or executable markup. Text renders as text nodes. New local assets
must be added explicitly and sorted in release/allowlist.json, with accurate
dimensions and source rights; run asset/content and browser checks.
The small deferred JS configuration loads before the main controller. Missing\ndata or an invalid schema preserves safe placeholders,
existing prices/gallery/contact and static FAQ. Do not rely on draft UI labels
as proof of independent content verification.

## Calculation / callback integration
See callback-estimate-contract.md in this directory. Wire estimate contains only
version1/master/grams/removal; backend recomputes sums. Same-origin capabilities
GET must support version1 before it can be attached. Ordinary callback remains
compatible with the current API. Unavailable support is explicit and user can
uncheck attachment. A visible local calculation is NOT proof it was transmitted.
No auto-send, no name/phone hacks. Local mocks are not real delivery.
Backend work is outside this frontend task and follows writer stop.

## Owner handoff
Supply: approved photo pairs + procedure/grams/master, attributed team portraits
and fields, genuine review links/quotes/display names, confirmed FAQ answers,
chosen public domain and approved legal/identity facts. These missing materials
do not block technical local preview. Editing bytes requires a new exact owner
preview; prior Night Luxury approval does not approve this new content.
Keep noindex/robots preview guard until later approved publication/domain review.
No push/merge/deploy/Google activation or real submissions in this task.
