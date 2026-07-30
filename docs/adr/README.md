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

## Adding one

1. Next number = highest here + 1. Filename `NNNN-kebab-slug.md`.
2. `status:` frontmatter is required (`accepted`, `superseded by ADR-NNNN`, …).
3. Add a row above — CI fails if the index drifts from the directory.
4. **Anchor it where the question arises.** Put a one-line comment at the code that looks
   wrong without the ADR. ADR-0005 exists because nothing in the `Dockerfile` said
   ffmpeg's absence was deliberate, so it read as an oversight — to a reviewer who had
   been told to read `docs/adr/` and found nothing there.
