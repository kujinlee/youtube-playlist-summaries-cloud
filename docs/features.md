# Feature map

**What this system does, what it deliberately does not, and where each is defined.** Rendered at
http://127.0.0.1:7391/features by `scripts/gen-features-page.py`; validated by
`scripts/check-features.py`.

**This file holds NAMES and PURPOSE, never STATE.** A node says what it is *for*; where it stands is
derived from the fragments beneath it. Do not add status, progress or "what's next" — a central file
that holds state drifts, and this project has measured that twice (see `docs/anchors.md`).

**Fragments attach through declarations that already exist.** An `anchors:` line names goals from
`docs/anchors.md`, which carry their specs, plans and ADRs with them; an `areas:` line names the
`(area)` tags `docs/backlog.md` rows carry. Every anchor and every in-use area is claimed by exactly
one node, so a rename or a new spelling turns the check red instead of vanishing from the page.

## PRODUCT

### summarise-a-playlist
state: built
for: Turns every video in a YouTube playlist into a summary a person can read.
anchors: cloud-publishing
areas: (product)

#### ingest-a-playlist
state: built
for: Brings a playlist's videos, titles and transcripts into the library so they can be summarised.
areas: (cloud)

#### magazine-rendering
state: built
for: Presents a finished summary as a laid-out page rather than a wall of text.
areas: (product / renderer)

### browse-the-library
state: built
for: Lets a person find a playlist, a video and its summary among everything they have ingested.
areas: (cloud/frontend), (cloud/UX)

### dig-deeper
state: built
for: Expands one section of a summary into a longer explanation, on request, for the sections a reader chooses.
areas: (product / dig-deeper)

#### dig-job-recovery
state: absent
for: Un-sticks a dig job whose worker went to sleep at the wrong moment.
expected-because: dig inherits the same worker exit-window race a summary does, but `listByPlaylist` hard-filters `job_kind = 'summary'` (lib/storage/supabase/supabase-job-queue.ts:28), so the read-path recoverer in app/api/jobs/route.ts cannot see it.

### correct-a-summary
state: built
for: Lets a reader fix something a summary got wrong and get the corrected version back.
anchors: corrections-in-cloud
areas: (cloud/quality)

### share-and-export
state: built
for: Lets a summary be read by someone without an account, and taken away as a PDF or an HTML document.
anchors: share-and-download

#### shared-dig-deeper
state: absent
for: Lets a reader who arrived by a share link expand a section the way its owner can.
expected-because: the share route renders with `dig: false` (app/s/[token]/route.ts:110), so the same document is deeper for its owner than for the person they sent it to — a difference the share link does not announce.

### sync-with-a-local-vault
state: built
for: Keeps one video's summary coherent between a person's local vault and the hosted copy.
anchors: cloud-sync

## PLATFORM

### job-queue-and-worker-lifecycle
state: built
for: Runs summarisation work in the background, one job at a time, without losing it or paying for it twice.
areas: (worker)

#### wake-on-visit
state: built
for: Lets the service sleep when there is nothing to do and come back when a visitor causes work.
areas: (ops)

### bounded-serve-path
state: built
for: Keeps the work one request performs bounded, and its lease alive for as long as that work runs.
anchors: serve-path-bounding

### spend-control
state: built
for: Keeps one generation paid for once, and the total spend under a ceiling the operator chooses.
anchors: serve-money-guard
areas: (cloud/money), (cloud / money)

### artifact-addressing
state: built
for: Gives a stored artifact an address that survives a title change and a re-summarisation.
anchors: stable-blob-addressing
areas: (product / addressing)

#### blob-key-encoding
state: built
for: Lets a video titled in any language be stored in and served from cloud storage.
anchors: cloud-blob-key-encoding

### concurrency-safety
state: built
for: Keeps two writers that touch one video from producing a result neither of them intended.
areas: (concurrency safety)

### access-control
state: built
for: Keeps a person's playlists, summaries and stored files reachable only by them and by whoever they share with.
areas: (cloud/security)

## DEV INFRASTRUCTURE

### deploy-verification
state: built
for: Proves by machine that what serves production is what was meant to ship.
anchors: prod-smoke
areas: (deploy / gates)

### automated-test-suites
state: built
for: Gives every change a machine-checked account of what it did to behaviour.
areas: (cloud/test), (test infra)

### guard-and-gate-harness
state: built
for: Gives the rules this project works by a mechanical enforcer, instead of a reader who has to remember them.
areas: (tooling)

### status-pages
state: built
for: Lets a person who was away see where the work stands and what needs a decision from them.
anchors: status-visibility
areas: (comprehensibility)

#### feature-map
state: built
for: Lets anyone find what the system does, what it omits on purpose, and the fragments that define each.
anchors: feature-map

### explainer-pages
state: built
for: Lets a person have a subject they choose explained in a page they can ask questions inside.
anchors: explanation-on-demand

### review-loop
state: built
for: Lets a review loop choose its own next step from recorded evidence rather than from recall.
anchors: review-decides-itself
areas: (process)

### process-harness
state: built
for: Makes the way this project is built reusable by another repository, rather than resident in this one's habits.
areas: (process / deliverable #2)
