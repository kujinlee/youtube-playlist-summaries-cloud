# Feature map

**What this system does, what it deliberately does not, and where each is defined.** Rendered at
http://127.0.0.1:7391/features by `scripts/gen-features-page.py`; validated by
`scripts/check-features.py`.

**This file holds NAMES and PURPOSE, never STATE.** A node says what it is *for*; where it stands is
derived from the fragments beneath it. Do not add status, progress or "what's next" — a central file
that holds state drifts, and this project has measured that twice (see ADR-0010).

**Fragments attach through declarations that already exist.** A spec or plan names its node by slug
in its own `> **Anchor:**` header; an `adrs:` line names the decisions a node rests on; an `areas:`
line names the `(area)` tags `docs/backlog.md` rows carry. This file is the ONE list of names
(ADR-0016): a header naming no current slug turns `check-anchors` red, and every in-use area is
claimed by exactly one node, so a rename turns the check red instead of vanishing from the page. Areas compare PER TAG
and normalised — `(cloud/money)` and `(cloud / money)` are one tag, so write it once — and a tag is
claimed by the nearest area that equals it or is a family above it. A row carrying several tags,
`(tooling) (comprehensibility)`, appears under the node claiming each one.

## PRODUCT

### summarise-a-playlist
state: built
for: Turns every video in a YouTube playlist into a summary a person can read.
areas: (product)

#### cloud-publishing
for: Summaries are produced and published by a hosted service, not only by a local vault.
adrs: 0001, 0005

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

### corrections-in-cloud
state: built
for: Lets a reader fix something a summary got wrong and get the corrected version back.
areas: (cloud/quality)

### share-and-download
state: built
for: Lets a summary be read by someone without an account, and taken away as a PDF or an HTML document.
adrs: 0003

#### shared-dig-deeper
state: absent
for: Lets a reader who arrived by a share link expand a section the way its owner can.
expected-because: the share route renders with `dig: false` (app/s/[token]/route.ts:110), so the same document is deeper for its owner than for the person they sent it to — a difference the share link does not announce.

### cloud-sync
state: built
for: Keeps one video's summary coherent between a person's local vault and the hosted copy.
adrs: 0002

## PLATFORM

### job-queue-and-worker-lifecycle
state: built
for: Lets a person ask for a whole playlist and walk away, without losing work they have paid for.
areas: (worker)

#### wake-on-visit
state: built
for: Keeps an idle service cheap to leave running, without a visitor paying for that in waiting.
areas: (ops)

### serve-path-bounding
state: built
for: Keeps a reader's wait for a summary short and predictable, however much work it takes to produce.

### spend-control
state: built
for: Keeps one generation paid for once, and the total spend under a ceiling the operator chooses.
areas: (cloud/money)

#### serve-money-guard
for: Serving a summary cannot spend money twice, and the protection is enforced rather than accidental.
adrs: 0008

### stable-blob-addressing
state: built
for: Gives a stored artifact an address that survives a title change and a re-summarisation.
adrs: 0006, 0007
areas: (product / addressing)

#### cloud-blob-key-encoding
state: built
for: Lets a video titled in any language be stored in and served from cloud storage.
adrs: 0009

### concurrency-safety
state: built
for: Keeps two writers that touch one video from producing a result neither of them intended.
areas: (concurrency safety)

### access-control
state: built
for: Keeps a person's playlists, summaries and stored files reachable only by them and by whoever they share with.
areas: (cloud/security)

## DEV INFRASTRUCTURE

### prod-smoke
state: built
for: Proves by machine that what serves production is what was meant to ship.
areas: (deploy / gates)

### automated-test-suites
state: built
for: Gives every change a machine-checked account of what it did to behaviour.
areas: (cloud/test), (test infra)

### guard-and-gate-harness
state: built
for: Gives the rules this project works by a mechanical enforcer, instead of a reader who has to remember them.
areas: (tooling)

#### review-process
state: built
for: Runs the dual adversarial review loop and records its rounds, verdicts and merge holds as evidence a machine can read.
areas: (tooling/review)

#### mutation-and-test-quality
state: built
for: Proves the tests and guards can fail — the mutation harness, its pins and sweep, and self-test cases that pass for the right reason.
areas: (tooling/mutation)

#### hooks-and-session-continuity
state: built
for: Carries work across turns, compactions and sessions — the Claude Code hooks, the in-flight ledger, usage pacing and stall detection.
areas: (tooling/hooks)

#### backlog-and-page-tooling
state: built
for: Turns the backlog, goal tree, dashboard and explainers into pages a person can read, and serves them.
areas: (tooling/pages)

#### guard-soundness
state: built
for: Makes each guard check what it claims to — no false green, no copy of a rule that drifts, no gate that can be walked past.
areas: (tooling/guards)

### dev-speed
was: dev-speed-first, harness-speed
for: A change gets its verdict as fast as the evidence allows, with mutation coverage identical.
areas: (tooling/speed)

### status-visibility
state: built
for: Lets a person who was away see where the work stands and what needs a decision from them.
areas: (comprehensibility)

#### feature-map
state: built
for: Lets anyone find what the system does, what it omits on purpose, and the fragments that define each.
areas: (comprehensibility/feature-map)

#### goal-tree
state: built
for: Shows every thread of work under the owner request it serves, what waits on the owner, and which plans are not ticked closed — at http://127.0.0.1:7391/goal-tree.
areas: (comprehensibility/goal-tree)

#### work-lines
state: absent
for: Drew every plan as a line back to the plan it branched from.
expected-because: retired 2026-10-28 into the goal-tree node above (the owner's decision D2, backlog #389) — two pages answering which threads are live left the reader with neither; a frozen record of it, with plan contents withheld pending backlog #194, is at http://127.0.0.1:7391/work-lines-archive.

### explanation-on-demand
state: built
for: Lets a person have a subject they choose explained in a page they can ask questions inside.
areas: (comprehensibility/explainers)

### review-decides-itself
state: built
for: Lets a review loop choose its own next step from recorded evidence rather than from recall.
adrs: 0014
areas: (process)

### process-harness
state: built
for: Makes the way this project is built reusable by another repository, rather than resident in this one's habits.
areas: (process / deliverable #2)

#### harness-ships-elsewhere
state: absent
for: Lets someone who has never seen this repository install the harness and use it in their own.
adrs: 0015
expected-because: the harness is written down but has never been installed anywhere else. Its own coupling measurement puts 9 repo-specific items in `brief/SKILL.md`'s ground-truth command list alone — 4 bare guard names, 4 document paths and 1 tool name, belonging to this repo's process rather than to any plugin — so a component can read as project-independent and still be unusable. (Corrected 2026-10-16 by the marketplace-inventory round-1 review: the literal `scripts/check-*` does not occur in that file, and 5 of the 9 are neither paths nor file invocations, so a path-and-invocation scan cannot see them.)
