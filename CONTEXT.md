# Domain Glossary

## Async Jobs (Cloud)

The vocabulary for the cloud-only durable work queue that runs expensive generation off-request. The local single-user tool has no jobs — it runs the same work inline. These terms name the *cloud* concept only.

- **Job** — a cloud unit of durable, asynchronous generative work: one (work target, job kind, job version) the cloud queue runs off-request while the client polls for its result. A completed Job's output is a committed, promoted artifact (see Storage Seam). **Distinct from the local `job-registry` "job,"** which is a whole in-memory *playlist-ingestion run* (one per output folder, ephemeral, SSE-streamed). The two coexist: the local single-user tool keeps its coarse in-memory job; the cloud uses the fine-grained durable Job.
- **Work target** — the fully-qualified subject a job produces for, and what makes two jobs "the same work." A **summary** job's work target is the **(playlist, video)** pair; a **dig** job's work target is the **(playlist, video, section)** triple, because dig deeper operates on a single summary section. The **playlist** coordinate is load-bearing: a video legitimately belongs to more than one playlist, and each playlist stores its **own** copy of that video's summary (artifacts are addressed per playlist — `owner/playlist/…`, matching the local per-output-folder model). Omitting it would join two summary jobs for the same video under different playlists into one, and only one playlist would ever receive its artifact. Two jobs with the same work target (and job version) are the same unit of work — joined/deduplicated, never run twice. Do **not** identify a job by video alone: that collides digs on different sections, and summaries under different playlists. In the cloud-only `jobs` table this coordinate is the concrete `playlistId` (the `playlists.id`), not the abstract index key.
- **Job version** — the artifact version a job produces, expressed as the target **`DocVersion`** (`{major, minor}`), not an arbitrary counter. Together with the work target it forms a job's identity: a request at the same (work target, job version) joins/returns the existing job — no re-run, no re-charge — while a request after the `DocVersion` major advances is legitimately new work. This ties "re-run a job" to a real format advance (the resummarize semantics), never to a client bumping a number.
- **Job kind** — the category of generative work a job performs: **`summary`** (produce a video's summary) or **`dig`** (elaborate a single section into the dig-deeper doc). Names the *operation*, distinct from **artifact** (a produced blob). Part of a job's identity: (work target, job kind, job version).
- **Status** — a Job's **lifecycle state**: `queued → active →` one of `completed | failed | dead_letter | cancelled`. This is the load-bearing state machine the queue drives and gates every transition on; it is what makes work correct (idempotency, leasing, retry, dead-lettering all key off status). Distinct from **progress phase**, which is advisory. `failed` = the handler declared the error not worth retrying; `dead_letter` = a retryable error that exhausted attempts (including crash-loops). Both are terminal.
- **Progress phase** — the **advisory, display-only sub-state of an `active` Job**, naming where within execution it currently is (`transcribing → summarizing → writing` for a summary; `digging` for a dig). It exists so the polling client can show "Processing… (summarizing)". **Always qualified as "progress phase"** — never bare "phase" — because the lifecycle **status** transitions are loosely "phases" too, and the two must not be confused. A progress phase never gates a state transition and is `null` whenever the Job is not `active`. Losing or skipping it is harmless; losing a status change is not.
- **Producer** — the cloud request path that turns a playlist ingestion request into Jobs: it resolves the playlist to its concrete `playlistId`, fetches the playlist's videos, and **enqueues one `summary` Job per video**. The producer is the **enqueue** side of the queue — distinct from the **worker** (the lease/consume side) and the **polling client** (the read side). It runs as the authenticated **owner** (RLS-scoped), never `service_role`.
- **Fan-out** — the producer's one-request-to-many-Jobs expansion: a single playlist request enqueues N per-video summary Jobs, not one batch Job. It is the cloud counterpart to the local tool's single in-memory playlist-ingestion run — the *same* work, sliced into independently-durable, independently-idempotent units (contrast the two "job" senses under **Job**). Fan-out is **best-effort**: a per-video enqueue failure records that video's error and continues; the request never rolls back the Jobs already enqueued.
- **Rollup** — the aggregate view of a fan-out's Jobs that the polling client reads: per-status counts plus a `total` and a `terminal` flag over the whole set. `terminal` is true **only** when `total > 0` and every Job holds a terminal status — an empty or unknown set is deliberately **not** terminal, so "nothing enqueued yet" never reads as "done".
- **Terminal (status)** — a Job **status** with no further transition: `completed`, `failed`, `dead_letter`, or `cancelled`. The polling client stops once every Job in a rollup is terminal, and a cooperative cancel applies only to **non-terminal** Jobs. Distinct from **progress phase**, which is advisory and never "terminal."

## Storage Seam

The vocabulary for *whose* data a storage operation targets and *which* collection it selects — introduced so one set of consumers can run against either the local single-user tool or the multi-tenant cloud backend without knowing which.

- **Principal** — the identity a storage operation acts on behalf of, plus the selector for which index it targets. Every storage operation takes an explicit Principal; there is no ownerless path. Locally it is a fixed single-user sentinel; in the cloud it is the authenticated (or anonymous) user.
- **Owner** — the tenant a Principal represents. Locally always the same single user; in the cloud the `auth.uid()` that RLS isolates data by. One owner's data is never visible to another.
- **Index key** — the backend-neutral selector for *which* playlist index a Principal targets. Locally it resolves to an **output folder** (a real on-disk data root); in the cloud it resolves to a **playlist key** (the YouTube list-id). The abstract concept is the *index key*; "output folder" and "playlist key" are its two concrete realizations. Do **not** call the abstract selector an "output folder" — that name is only correct for the local realization. Not to be confused with **`playlistIndex`** (a video's *ordinal position* within a playlist — a number); the index key selects *which* playlist, `playlistIndex` says *where in it* a video sits. The two are unrelated.
- **Output folder** — the concrete local data-root directory a user chooses for a playlist's artifacts (persisted on the playlist index). A valid term for the *local* concept only; it is one realization of an index key, not the abstract selector.

### Artifacts

The files a playlist produces, split by whether they can be rebuilt:

- **Source-of-truth blob** — an artifact that cannot be recreated for free: the **summary** (Markdown) costs a Gemini call and would come back *different*; a **slide screenshot** requires re-downloading the video and cannot be recaptured at all on a hosted server. If a source blob goes missing, the system enters **repair needed** — it must surface the gap, never silently regenerate.
- **Derived-cache blob** — an artifact that is a deterministic render of a source (the rendered **HTML doc**, the **PDF**). Safe to lose and rebuild from the source with no model call. A missing derived-cache blob simply regenerates.
- **Repair needed** — the state of an artifact whose source-of-truth blob is committed in the index but absent from storage. Distinct from "not yet generated" (never produced) and from a missing derived cache (silently rebuilt).
- **Promoted** — an artifact whose blob has completed its final write and is safe to serve. An artifact that is *committed* (the index references it) but not yet *promoted* may still be finalizing; readers treat it as not-yet-available rather than broken.

## Personal Review

A user-authored evaluation of a video, consisting of an optional **personal score** (integer 1–5) and an optional **personal note** (free text, max 500 characters). Stored in `playlist-index.json` alongside AI-generated ratings. Distinct from AI-generated ratings in that it reflects the user's own judgment about usefulness and revisit priority.

- **Personal score** — the 1–5 star rating the user assigns to a video. `undefined` means the video has not been reviewed yet (unscored).
- **Personal note** — a brief free-text comment the user leaves on a video (max 500 characters). `undefined` means no note has been written. The table preview shows the first 25 characters.

A video with no personal score and no personal note has **no personal review**.

**Unscored** — a video where `personalScore` is `undefined`. Dimming in the table is triggered by unscored status only; a video with only a personal note is not considered unscored.

## AI Ratings

The five scores (usefulness, depth, originality, recency, completeness) and the derived `overallScore` generated by Gemini during ingestion. These are distinct from a personal review — they are not editable by the user.

In the UI, the filter for `overallScore` is labelled **"AI score ≥"** to distinguish it from **"My score ≥"** (personal score filter). Both use the same `≥ N` shape.

## Detail Layer

The skim-level artifact is the **summary**. Below it sits a detail layer, generated on demand per section.

- **Dig deeper** — the reader action (and the control that triggers it) of asking for a deeper, video-grounded treatment of a single summary section. The control is also the navigation affordance to the resulting detail.
- **Dig-deeper doc** — the per-video artifact that accumulates dug sections over time. It is the live detail layer: built lazily, one section at a time, only for sections a reader chose to dig. Distinct from the deep-dive doc.
- **Deep-dive doc** — the legacy artifact: a whole-video analysis generated up front in one pass. Frozen — no new ones are produced. The dig-deeper doc replaces it as the detail layer; existing deep-dive docs remain readable but are not the live concept.

A summary section that has been elaborated into the dig-deeper doc is **dug**; one that has not is **undug**.

- **Section sub-heading** — a heading (rendered `<h3>`, authored as `###`) that divides a single dug section's elaboration into labeled subsections (e.g. "How it works", "Where it breaks down"). Present only when a section's prose is long enough to warrant structure; a short dug section has none. It is never the section's own title (that remains the `<h2>` numeral + title). Distinct from **sub-title** — a single tagline under a title — which this project deliberately does **not** use. Do not call it a "subtitle" (that reads as a video subtitle/caption track).

- **Slide** — an informative on-screen visual in the video worth capturing because it conveys something the speech alone does not. Defined broadly: a presentation slide, a diagram, a chart, or a code/terminal/screen demo. Not every on-screen moment is a slide — only one that adds information beyond what is said.
- **Slide screenshot** — the captured still image of a slide, embedded inline in the dig-deeper doc at the point in the elaboration where it is relevant.
- **Slide caption** — the short plain-English description of a slide screenshot, authored by Gemini at generation time and carried as the screenshot's alt text. Rendered (optionally) as a visible `<figcaption>` beneath the screenshot. **Always qualified as "slide caption"** — never bare "caption" — to avoid collision with **captions** in the YouTube sense (the transcript/caption tracks used for transcript sourcing; see "caption-gated" videos). The two are unrelated concepts.
