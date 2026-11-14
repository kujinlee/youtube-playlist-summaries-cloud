---
name: anchor-name-and-stable-id-handoff
description: "FIRES-WHEN: resuming stable blob IDs, anchors, ADR-0010 or M4/M5 — ⭐ RESUME HERE for stable blob addressing. M4 MERGED (PR #155, c517faa) AND APPLIED TO PROD 2026-08-27 14:01 UTC — 0027 IS LIVE; next is M5 (write-path cutover). The roadmap EXISTS (2026-08-22-append-only-generations-roadmap.md) — I once failed to find it and re-derived it wrongly"
metadata: 
  node_type: memory
  type: project
  originSessionId: 92595a72-4e72-4cb8-9e2c-8cddc19a2bb3
  modified: 2026-08-28T04:54:59.767Z
---

**CURRENT STATE (verified against the repo 2026-11-14):**
- **The spine is** `docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md` — milestones
  M1–M7 for stable blob addressing. **Read it; do not re-derive it.** Its M4 section is marked DONE and
  names **M5 — write-path cutover** as next: the schema is live and inert, no application caller reaches
  `record_artifact` yet, which `scripts/check-paid-caller-arrival.py` watches for.
- **M4 MERGED 2026-08-27, PR #155, squash `c517faa`** — `supabase/migrations/0027_stable_blob_addressing.sql`
  (142,832 bytes, 1,898 lines, 161 catalog objects). **Applied to PRODUCTION 2026-08-27 14:01 UTC** —
  measured over `claude_ro`: all five relations (`workspaces`, `workspace_videos`, `video_generations`,
  `video_artifacts`, `video_artifact_sources`) live with `relrowsecurity` and `relforcerowsecurity` true
  and one owner-read policy each; prod and local agreed on all 18 `public` tables. ⛔ Do NOT repeat the
  stale "prod is still 0026 / M4-β not given" claim.
- **ADR-0006** (blob addresses derive from immutable identity) and **ADR-0007** accepted 2026-08-24 (M3,
  PR #148, `61d91c0`). **ADR-0002 is PARTLY superseded** — only its rejection of video-level shared
  summaries falls; its `(playlist_id, owner_id)` cross-tenant guard STANDS. ADR-0009 (encoder) accepted.
- **ADR-0010** (documents declare their anchor) — shipped by PR #146 + PR #147 (`b4223f5`):
  `docs/anchors.md`, backfilled `Anchor:`/`ADR:`/`Goal:` headers, `scripts/check-anchors.py` (in CI).
  ⚠ **Its front matter still reads `status: proposed — accepted when the header check ships and passes on
  the living set`** (2026-11-14) although that condition is met — flipping it is a human gate, still undone.
  ⚠ The check cannot tell whether a `Goal:` line is TRUE.

**Rules worth keeping:**
- **Verify prod by reading prod, in both directions.** Prod once sat eight days behind a migration while
  documents said "done" ([[process-conventions]]); this file then shipped the inverse error.
- **The ADR number is the identifier that survives a rename;** an `Anchor:` name is the primary key (not
  every goal has an ADR). *A central file that holds NAMES is safe; one that holds STATE drifts.*
  **Declare upward in the document, derive downward by aggregation.** **DO NOT rename existing files**
  (user decision).
- **ACCEPTED IS NOT IMPLEMENTED,** and an ADR's front matter can be broader than its Consequences
  section (ADR-0006 said "supersedes ADR-0002"; trusting it would have retired a live guard). See
  [[true-about-the-name-silent-about-the-layer]].

## History
- **2026-08-24, the miss:** I could not find the roadmap and spent ~an hour re-deriving it, claiming "17
  rounds never converged, so cut scope" — its M3 already quoted r17: *"stop reviewing this document and
  start task #36 … the next genuine test is the migration, not round 18"* (Blockings 4→3→1→1). My
  "minimal slice" proposal was WITHDRAWN. Two causes: `ls docs/superpowers/plans/ | head -20` over an
  82-file dir with the file at position 80, and a plan named for the mechanism rather than the anchor.
  User: *"'stable blob addressing' was the good name. Renaming it to 'append-only generations' wasn't a
  good move."* → backlog #64 (closed ✅), PR #145 (`fe1328e`), ADR-0010.
- **M3 lessons:** 8 of round 17's 9 findings were already applied — verified by reading each `⟳ round 17`
  marker; the one live residue was in design spec §5.1, where ADR-0007 said it was.
- **M4 merged with review residue:** rounds 10+11 found 1 Blocking · 8 High · 8 Medium · 6 Low, none in
  `0027` — all in instruments; instrument hardening became its own slice (user decision 2026-08-27, my
  to-do note #156). Each fix round caused the next round's worst finding (r10 `set -uo pipefail` → r11
  B1; r10 regex scanner → r11 H1, 240 comments misread).
- ⚠ **Unfiled as of 2026-08-27:** `M1`/`M2`/`M3` meant different things in `roadmap-to-launch.md`
  (Deploy · Sync · Acceptance) and the spine (honest card · corrections-in-cloud · discharge-the-design-gate)
  — a live instance of backlog #39. Not re-checked 2026-11-14.
- Older dated blocks (2026-08-25/26 states, fork (a)) are kept verbatim in [[m4-superseded-trail]].
