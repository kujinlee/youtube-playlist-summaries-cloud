---
name: cloud-dig-serving-branch-state
description: "FIRES-WHEN: changing the cloud dig serve path (type=dig-deeper, dig-state, loadDigForServe), or a jest.spyOn throws 'Cannot redefine property' — MERGED PR #19 (daa6c68, 2026-07-14); serve never charges"
metadata:
  type: project
  originSessionId: 7746a733-7051-4952-85dd-526eb71dd21b
---

**STATE:** MERGED to master — PR #19, squash `daa6c68` (2026-07-14). Serves per-section dig blobs as a merged
skim+dig HTML doc at `type=dig-deeper`, plus a cloud dig-state endpoint (§14.2 of the dig-generation spec, PR
#15). The frontend that makes it reachable shipped as PR #20 ([[cloud-dig-deeper-frontend-state]]).

**RULES — locked design:**
- **Money invariant: dig serve is a pure blob read + render** — never `resolveMagazineModel` /
  `reserve_serve_model` / `resolveAndParse` / generate. Measured before merge: spend_ledger 0→0.
- **Local off-path byte-identical:** the readOnly static render mode omits nav-coupled controls and nonces all
  scripts; default off.
- **dig-state REUSES `loadSummaryForServe` wholesale** (gate + base agreement with the loader) and is
  filename-authoritative: a section is dug on blob presence. **M1 ACCEPTED BY DESIGN** — under blob corruption
  dig-state may over-report vs the rendered doc (the loader parses and skips malformed); no money/isolation impact.
- Blob key `dig/{base}/{sectionId}.r{DIG_GENERATOR_VERSION}.md` — version is **9** (`lib/dig/generate.ts`,
  verified 2026-11-14). Slide tokens → caption-only placeholder.

**Repo gotcha (applies broadly):** `jest.spyOn(namespace,'fn')` on `import * as X` THROWS "Cannot redefine
property" under Next16/SWC jest → use `jest.mock('@/path')` automock + `(fn as jest.Mock).mockX()`, and
`jest.requireActual` for positive controls.

## History
Real-render verified before merge with a throwaway integration smoke against live local Supabase (200 html,
nonce CSP, `[[SLIDE:…]]`→`🖼 caption`, 9 scripts + 1 style nonced, dig-state `{sectionIds:[65]}`) — the serve
path had no committed integration test until PR #20 added one. Spec `0f04615`+`1c7cd00`; plan `d1a7af4`;
post-plan review v1 `159646d` (3B+5H) → v2 `68ccbd2` converged; six SDD tasks `ff4f96a` … `1988351`; whole-branch
dual review (Codex + Claude) CONVERGED 0B/0H at `5f19bd8`
(`docs/reviews/whole-branch-cloud-dig-serving-review.md`). Suite 2265/2265, tsc 0.
See [[frontend-subproject-design-state]], [[local-cloud-validation-run]], [[process-conventions]].
