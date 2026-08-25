# Architecture Decision Records

Decisions a future reader would otherwise **reverse by accident**. Each one answers a
question the code cannot: why this shape, and what was rejected.

`improve-codebase-architecture` (dev-process Phase 6) reads this directory before every
architecture review, and must **not** re-litigate what is recorded here. A decision that
is not in this directory is, in practice, a decision a future review will propose undoing.

**When does a decision belong here?** See
[`.claude/skills/grill-with-docs/ADR-FORMAT.md`](../../.claude/skills/grill-with-docs/ADR-FORMAT.md)
→ *"When to offer an ADR"*. All three must hold: hard to reverse, surprising without
context, and the result of a real trade-off. The categories that catch the most misses are
**constraints not visible in the code**, **deliberate deviations from the obvious path**,
and **rejected alternatives whose rejection is non-obvious**.

`scripts/check-docs.py` (run in CI) keeps this index in sync with the directory and
verifies that every ADR reference in the codebase resolves.

## Index

| # | Decision | Answers |
|---|---|---|
| [0001](0001-hand-rolled-postgres-job-queue.md) | Hand-rolled Postgres job queue instead of pg-boss | "Why not use a queue library?" — RLS-owner-scoping, a domain idempotency tuple, and being the FK anchor for the spend reservation |
| [0002](0002-playlist-in-job-identity.md) | Playlist is part of a job's identity | "Why is the same video summarized twice?" — artifacts are per-playlist; omitting the playlist joins two jobs and starves one playlist of its artifact |
| [0003](0003-cloud-pdf-serve-side-not-a-job.md) | Cloud summary PDF is a serve-side cached blob, not a durable Job | "Why isn't the PDF a Job like everything else, and why does it skip commit→promote staging?" — it is a derived-cache blob, not source-of-truth generative work |
| [0004](0004-cost-caps-are-tunable-soft-targets.md) | Cost caps are tunable soft targets, enforced today as a hard ceiling | "Can I change this cap?" — yes; the CI guard test is a deliberate posture, not a law |
| [0005](0005-hosted-never-downloads-youtube-video.md) | The hosted product never downloads YouTube video | "Why is there no ffmpeg in the Dockerfile?" — Terms of Service, not packaging. Server-side capture is forbidden **by any tool**, including the Chromium already in the image |
| [0006](0006-stable-blob-addressing.md) | **PROPOSED** — blob addresses derive from immutable identity, not display attributes | "Why isn't the summary at `003_alpha.md` any more?" — a serial/slug address is mutable, and every change orphaned paid Gemini artifacts. Supersedes 0002's cost-based rejection of video-level sharing |
| [0007](0007-artifacts-are-an-append-only-log.md) | **PROPOSED** — artifacts are an append-only log; nothing coordinates writers | "Why is there no lease on `video_artifacts`?" — a producer writes a NEW generation and a replicator copies an EXISTING one, so their writes land on different keys and cannot collide. The reservation protocol re-solved a problem 0006 had already dissolved, and failed six consecutive review rounds doing it. Supersedes that protocol. **Scoped to COORDINATION only** — render *addressing* was split out 2026-08-09 after two designs were refuted in two rounds (brief: `docs/superpowers/specs/2026-08-09-render-addressing-brief.md`, backlog #25). Two caveats worth knowing before reading: the `model` kind is a paid producer with **no job** (arbitrated by `serve_model_charge`), and the `generation_id IS NULL` conflation this ADR was drafted to dissolve is **still open** |

| [0008](0008-serve-money-guard-depends-on-storage-grant-granularity.md) | The serve-path money guard is corroboration-by-ordering, and depends on the storage grant staying coarse | "Why is there no permission check before the serve path spends money?" — because the caller already read the markdown from the same folder and failed closed. That is only evidence because `0007`'s grant is on the owner path segment. **Narrow the grant and the guard silently dies** — 6¢ → 12¢, every test green. The inverse of ADR-0005: the migration looks *fine*, so nobody goes looking |
| [0009](0009-logical-unicode-physical-ascii.md) | Logical keys are Unicode, physical keys are ASCII, and the storage seam owns the mapping | "Why is the object in the bucket called `003_=hXk3…md` when the title is Korean?" — Storage rejects every non-ASCII key with `400 InvalidKey`, *after* Gemini has been paid (backlog #36). One function converts, at one seam. The encoding is **one-way**, legal only because `list()` re-attaches the caller's own prefix instead of inverting it; it hashes **utf16le** because utf8 collapses unpaired surrogates to `U+FFFD` and one video's paid summary would overwrite another's. The owner prefix is deliberately **not** encoded, which is what keeps `0008` alive |
| [0010](0010-documents-declare-their-anchor.md) | **PROPOSED** — a document declares the goal it belongs to; the index over documents is derived, never maintained | "Why does every living spec carry an `Anchor:`/`ADR:`/`Goal:` header?" — because the plan for a goal became unfindable. Asked for the stable-addressing roadmap, I re-derived it over an hour and reached a conclusion the document had already corrected in itself. The feature spans **three vocabularies** after two honest renames and they share no keyword; keyword membership returns 7 of 162 specs/plans and misses a member the roadmap names in its own fifth line. **A central file that holds NAMES is safe; a central file that holds STATE drifts** — which is why the edge lives in the document and the index is generated. Records why a central relationship map and free-text tags were rejected: this repo already runs the first (`ROOTS`/`DEPENDS`), and its own roadmap lists two defects in it |

## Adding one

1. Next number = highest here + 1. Filename `NNNN-kebab-slug.md`.
2. `status:` frontmatter is required (`accepted`, `superseded by ADR-NNNN`, …).
3. Add a row above — CI fails if the index drifts from the directory.
4. **Anchor it where the question arises.** Put a one-line comment at the code that looks
   wrong without the ADR. ADR-0005 exists because nothing in the `Dockerfile` said
   ffmpeg's absence was deliberate, so it read as an oversight — to a reviewer who had
   been told to read `docs/adr/` and found nothing there.
