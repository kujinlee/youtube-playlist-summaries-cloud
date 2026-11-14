---
name: stage-1f-c-design-state
description: "FIRES-WHEN: citing Stage 1F-c (downloads: MD and rendered HTML), PR #9, or the format=/download= params on the serve routes — MERGED 4052c7d, 2026-07-10; closes Stage 1F"
metadata: 
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

**Stage 1F-c is MERGED** — PR #9, merge commit `4052c7d`, 2026-07-10. **Closes Stage 1F** (1F-a serve
[[stage-1f-a-design-state]], 1F-b share [[stage-1f-b-design-state]], 1F-c downloads). No deferred 1F-c items remain.

A summary doc can be downloaded as raw `.md` or self-contained rendered `.html`, by the **owner** (session) OR a
**share-token holder**.

**Scope (user-approved):** MD + rendered HTML only. **NO server-side PDF** (removed from the project 2026-06-30; PDF =
browser Save-as-PDF via the 1F-a print button). **NO Obsidian FSA** (deferred; "download the .md" covers it).

**Design (thin layer over 1F-a/1F-b):** `format=html|md` + `download=1` query params on the TWO existing serve routes
(`app/api/html/[id]` owner, `app/s/[token]` share) — not new routes. A download = an early MD short-circuit (after the
blob read, before any model resolution) + `Content-Disposition: attachment`. **Money invariants:** MD = pure
passthrough (never resolves the model, never charges, both paths); HTML reuses each caller's money path (owner
resolveMagazineModel materialize+charge-once; share readFreshMagazineModel never-charge). Shared pure-leaf helper
`lib/html-doc/file-response.ts` (RFC 5987 filenames + nosniff). `getShareServeContext` gains `title?`. The share MD
branch MUST run the mandatory pre-response re-check (D12/B10b). Inline md = `text/plain` + `nosniff`. The MD branch and
file-response.ts are inside the 1F-b B18/B18b/B18c money guards.

## History
- Chosen by user 2026-07-10 (they typed "1G-c", meant 1F-c). Branch `feat/stage-1f-c-downloads` off bb71d32.
- Spec v1 (1 Blk/2 High/2 Med/3 Low) → converged v4 in 3 rounds. Plan `docs/superpowers/plans/2026-07-10-stage-1f-c-downloads.md`,
  4 TDD tasks; Post-Plan Gate: Codex 0 Blk/0 High/1 Med, Claude 0 Blk/1 High/2 Med/2 Low, all test-infra → plan v2.
- Per-task dual review (Codex gpt-5.5 + Claude opus): T1/T2 single-pass; T3 §8 (1 Med dup-`format` bypass + 1 Low
  fixed); T4 §8 (0 findings both). Whole-branch opus review = Ship. Reviews `docs/reviews/{spec,plan,task}-1f-c-*`.
- Pre-merge fix M1: owner `video.title` non-string → 500; fixed by symmetric `unknown`-typed coercion (`6d979d1`) +
  integration test. Final: html-download 8/8, unit 1802/1802, tsc clean.
