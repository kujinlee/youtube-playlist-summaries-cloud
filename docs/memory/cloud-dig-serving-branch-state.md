---
name: cloud-dig-serving-branch-state
description: "FIRES-WHEN: resuming or citing cloud dig serving (PR #19) — Cloud dig serving — ✅ MERGED to master (PR #19, squash daa6c68); serve type=dig-deeper + cloud dig-state, real-render-verified"
metadata:
  type: project
  originSessionId: 7746a733-7051-4952-85dd-526eb71dd21b
---

**Cloud dig SERVING slice** (deferral §14.2 of the dig-generation spec PR #15): serve per-section dig blobs as a merged skim+dig HTML doc at `type=dig-deeper` + a cloud dig-state endpoint.

**STATUS: ✅ MERGED to master — PR #19, squash commit `daa6c68` (2026-07-14). Branch feat/cloud-dig-serving deleted (local+remote).**

**Real-render verified before merge:** a throwaway integration smoke (tests/integration/, deleted after) rendered the dig serve against live local Supabase — real storage/RLS/route → loadDigForServe → renderDigDeeperDoc → CSP, blob written by the real generation writer. All green: 200 html, `script-src 'nonce-…'` CSP, dug prose inline, `[[SLIDE:…]]`→`🖼 caption` placeholder, read-only (no dig-trigger/navScript), 9 scripts+1 style all nonced, dig-state `{sectionIds:[65]}`, spend_ledger 0→0 (no charge). NOTE: the serve path has NO committed integration test (only mocked unit tests) — a permanent version is a natural add for the frontend slice.

**Full gate trail (all committed on branch):**
- Spec `0f04615`+`1c7cd00`; Plan `d1a7af4`.
- **Post-Plan dual review CONVERGED:** v1 `159646d` (3 Blocking + 5 High, all confirmed vs ground truth + fixed), v2 `68ccbd2` (0B/0H). Docs: `docs/reviews/plan-cloud-dig-serving-v1-review.md`, `-v2-rereview.md`.
- **6 SDD tasks, each two-stage-reviewed clean:** T1 parse blob `ff4f96a` · T2 BlobStore.list (isolation seam, leak-free) `c27fa5f` · T3 loadDigForServe (money guard non-vacuous) `dddf614` · T4 renderDigDeeperDoc readOnly+nonce (local byte-identical) `151d6c3` · T5 html dig branch (+.has() guard, no charge) `60be216` · T6 cloud dig-state (gate reuse, behavior-17) `1988351`.
- **Whole-branch dual review (Codex gpt-5.5 + Claude) CONVERGED 0B/0H** `5f19bd8` — `docs/reviews/whole-branch-cloud-dig-serving-review.md`. Both verified all §11 risk areas end-to-end (money invariant, owner isolation, shared-code byte-identity, version awareness).
- **Full suite 2265/2265, tsc EXIT=0.**

**M1 (only Medium, both WB reviewers) ACCEPTED BY DESIGN:** dig-state is filename-authoritative (spec §3 Unit C) — reports a section dug on blob presence, doesn't parse; the serve loader parses+skips malformed (behavior 19). Under blob corruption dig-state may over-report vs the rendered doc. No money/isolation impact, no live consumer (frontend deferred). Documented in spec addendum + code comment. Lows L1-L4 accepted (see WB review doc).

**Key design decisions (locked):** render = merged skim+dig (reuse renderDigDeeperDoc/mergeDigDoc); cached model read free (readModelEnvelope); slide tokens → caption-only placeholder; readOnly static render mode (omit nav-coupled controls, nonce all scripts, default off → local byte-identical). Money invariant: dig serve = pure blob read+render, never resolveMagazineModel/reserve_serve_model/resolveAndParse/generate. dig-state REUSES loadSummaryForServe wholesale (gate + base agreement with loader). Blob key `dig/{base}/{sectionId}.r{DIG_GENERATOR_VERSION=9}.md`.

**Repo gotcha surfaced (T3, applies broadly):** `jest.spyOn(namespace,'fn')` on `import * as X` THROWS "Cannot redefine property" under Next16/SWC jest → use `jest.mock('@/path')` automock + `(fn as jest.Mock).mockX()`, `jest.requireActual` for positive controls.

**NEXT SLICE (agreed 2026-07-14): cloud "Dig deeper" FRONTEND affordance** (gen-spec §14.3). Makes this serve slice reachable from the UI. STARTS WITH BRAINSTORMING → spec (human gate) — NOT code; it's a UI async-operation component so the spec must settle blocking-vs-non-blocking UX + URL-contracts table + overlay/dismissal table first. Scope: a "Dig deeper" affordance in the cloud video UI (`components/VideoMenu.tsx`/`VideoRow.tsx`/`cloud/CloudApp.tsx`) → link to `/api/html/[id]?playlist=…&type=dig-deeper` when dug + trigger `POST /api/videos/[id]/dig/[sectionId]?playlist=…` (already cloud-aware) for un-dug; dig-state polling to enable/show; progress-during-generation is an OPEN FORK — SSE (the `dig/[sectionId]/stream/` route looks LOCAL-ONLY, would need a cloud branch = backend work) vs dig-state polling. Reference UX: the LOCAL app already has a working dig-deeper frontend (interactive `renderDigDeeperDoc` trigger/expand/refresh + navScript/EventSource) — the cloud slice adapts it. Not in any standing grant; own spec+merge gate, fresh session. See [[frontend-subproject-design-state]].

**NEXT (human gate):** merge decision. Recommended: push → PR → merge via `gh --repo kujinlee/youtube-playlist-summaries-cloud`. On merge, per `superpowers:finishing-a-development-branch`. Uncommitted working-tree (do NOT commit): `supabase/config.toml`, `docs/local-validation-findings.md` (BUG-7 etc.), `.superpowers/`, `.codex-tasks/` (gitignored scratch). See [[local-cloud-validation-run]], [[process-conventions]].
