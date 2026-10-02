---
name: stage-2-batch-autonomy-plan
description: "FIRES-WHEN: planning the remaining sub-project 2 slices — Standing plan for Sub-project 2 remaining slices — batch-spec 2c+2d now, defer Stage 3, auto-merge each slice after dual-review convergence"
metadata: 
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

Decided 2026-07-11 (user, at the 2b spec-approval gate). Governs how the remaining
frontend slices run.

**Batching:** brainstorm specs for **2b → 2c → 2d back-to-back in one interactive
sitting** (all past the spec-approval gate), then implement each **in its own fresh
session** (fresh context per slice — do NOT run plan+impl for multiple slices in one
context; that risks context fillup + cross-slice error bleed). Durable handoff between
slices = committed spec + plan + SDD ledger (`.superpowers/sdd/progress.md`) + git +
this memory.
**RESLICE (2026-07-11, after 2c exploration):** the original "2c doc lifecycle" was NOT
a clean frontend slice — cloud PDF + deep-dive **generation** are local-only (in-memory
SSE, local FS) and need substantial NEW backend (Supabase blob storage, durable
serverless-safe jobs, and for deep-dive Gemini **charging + guardrails**). So doc
lifecycle is split:
- **2c (revised) = cloud doc CONSUMPTION** — view summary HTML (serveCloud route already
  works: `/api/html/[id]?playlist=<uuid>&type=summary`, CSP/nonce, artifact gate) +
  download MD/HTML (`format`/`download` params already work) + share-link create/copy/
  revoke UI (backend done Stage 1F-b, **zero UI exists** — net-new). All frontend over
  working backend. Batch-safe; spec now. (Absorbs the old "2d share+downloads".)
- **Cloud doc GENERATION (PDF + deep-dive) = deferred backend slice**, its own full
  spec+dual-review cycle (backend + money). NOT batched.
- **Stage 3 (Sync) is DEFERRED — do NOT batch it.** Spans cloud+local; spec after the
  cloud app is feature-complete.

So the batch this sitting = **2b spec (done) + 2c-consumption spec**. Generation +
Stage 3 are separate later cycles.

**Standing auto-merge authorization (this batch only):** for each of 2b/2c/2d, after
implementation → dual adversarial review to convergence (no new Blocking/High) → clean
whole-branch review → **auto-merge the slice PR to master**, then report the merge. This
is the user's durable merge-gate grant for this batch; still report each merge. Use
`--repo kujinlee/youtube-playlist-summaries-cloud` (two-remotes footgun, see
[[gh-two-remotes-footgun]]). Stage 3 is NOT covered — it needs its own merge gate.

**Notifications:** push to phone requires Remote Control paired AND user away from
terminal (pushes are suppressed as redundant while they're actively at the terminal).
Fire `PushNotification` at AFK checkpoints (task/slice boundaries = safe-to-compact
points). No reliable self-measure of context-fill %, so notify at boundaries, not a %
threshold.

**Branches / spec commits:**
- 2b spec: `32ff180` on `feat/stage-2b-cloud-ingest` (cut from master@4c0109b).
- 2c spec: `3b98fe4` on `feat/stage-2c-cloud-doc-consumption` (cut from master@4c0109b,
  i.e. BEFORE 2b merges). **2c impl session must `git merge master` (post-2b-merge)
  before implementing** — 2b and 2c both touch the cloud `VideoMenu` + `listVideos`
  serveCloud DTO, so 2c needs 2b's merged code first. Implement in order: 2b → 2c.

**Batch complete for this sitting = 2b + 2c specs approved.** No 2d/generation/Stage 3
specs this batch (generation + Stage 3 are separate later cycles). Next: per-slice fresh
sessions — writing-plans → Post-Plan Gate → SDD impl → dual-review convergence →
auto-merge. See [[frontend-subproject-design-state]].

**2b IMPL IN PROGRESS (2026-07-11, on `feat/stage-2b-cloud-ingest`):** plan written
(`docs/superpowers/plans/2026-07-11-stage-2b-cloud-ingest.md`), 10 TDD tasks. Post-Plan
Gate dual-review converging: v1 `17f5f57`; R1 (Codex+Claude) found 3 Blocking + 5 High →
v2 `7040d8d`; R2 found 1 Blocking + 3 High (all Task-7 test fixtures + wiring; component
logic confirmed fixed) → v3 `2d9e316`; R3 running. Reviews saved to
`docs/reviews/plan-2b-cloud-ingest-{codex,review,codex-v2-rereview,v2-rereview}.md`.
Key design facts locked: 2b = ZERO backend change (playlistKey/playlistUrl already in
DTOs); only shared-lib touch = `pollUntilTerminal` gains onProgress/isFatal/AbortSignal/
{aborted} (Task 1); banner is probe-first + cancellable; REAL tokens are `--surface-*`/
`--text-primary`/`--warning` (NOT --bg/--text/--warn). When R3 converges (no new
Blocking/High): SDD impl (T1→T10) → whole-branch review → auto-merge. Then 2c (`git merge
master` first). Gate checklist = TaskCreate #51-54.

**2b POST-PLAN GATE CONVERGED (2026-07-11).** Plan v5 = `eef22a7` (final), 4 dual-review rounds.

**✅ STAGE 2b MERGED to master — PR #12, merge commit `76e0590` (2026-07-11).** All 10 tasks
implemented via superpowers:subagent-driven-development, each with per-task Claude+Codex dual
review to convergence. **Adversarial-review yield (why the process paid off): 6 real Highs the
implementation AND the Claude approval-pass missed, caught by Codex (or the whole-branch pass)
and fixed** — T1 2× abort-contract races in the cancellation primitive; T2 null-body TypeError
crash + a Retry-After rate-limit regression the fix itself introduced; T6 double-submit spend
re-entrancy (modal); T7 fireIfAdvanced fired on regressions not just advances; T9 retained
playlistUrl → wrong-playlist Refresh (a spend-path hole the plan's own 4 rounds missed); and the
**whole-branch review caught a NEW Blocking no per-task review could see — Refresh (onRefresh)
was a 2nd createIngest spend path lacking the synchronous mutex the modal had** (fix `bb13c84`).
Pattern: on 5 of these, Claude approved / rated benign and Codex found the real defect — dual
review with an adversarial second model is load-bearing. Final: tsc 0, unit 1955/1955,
integration 331 pass/2 skip. Reviews in `docs/reviews/task-2b-*.md` + `whole-branch-2b-review.md`.
Deferred post-merge follow-ups (all confirmed non-blocking): abortableSleep clearTimeout timer
(browser no-op); banner role=status/aria-live a11y; onProgress-aborts-signal edge; display-only
stale-list/sort races.

**✅ STAGE 2c MERGED to master — PR #13, merge commit `db5cbfc` (2026-07-11).** 8 tasks via
subagent-driven-development, each per-task Claude+Codex dual review to convergence; Post-Plan Gate
3 dual-review rounds (2 High + several Medium fixed pre-code); whole-branch dual review CLEAN both
(0 Blocking/High). **Adversarial-review yield (why it paid off): Codex repeatedly caught structural
defects the Claude pass approved** — T5 guardedClose gated on state not the synchronous inFlightRef;
T7 ShareDialog invalid DOM nesting under `<tbody>` (needed a portal like CorrectionsPanel); T6 three
test-completeness gaps; T8 missing expires_at assertion; plus Post-Plan-Gate H (existing exact-shape
readIndex test broken by the new summaryReady:false). All fixed + re-reviewed to convergence. Final:
tsc 0, unit 1989/1989, integration 334 pass/2 skip. Reviews in `docs/reviews/task-2c-*` +
`whole-branch-2c-{codex,review}.md`. **Deferred 2c follow-ups (non-blocking):** (1) repeated "Create
link" mints multiple live tokens — SPEC §1-sanctioned, bulk revoke is the deferred share-management
slice; (2) ShareDialog reads `window.location.origin` above the SSR guard (safe-by-construction today);
(3) 0017 same-name DROP+CREATE deploy-skew (atomic deploy documented in the plan's Task 1 note);
(4) revoke `{revoked:false}`-as-success (plan L2, accepted).

**BATCH COMPLETE (2b + 2c both merged).** The current auto-merge grant covered 2b/2c only — it is now
**spent**. Remaining Sub-project 2 work is NOT in any standing grant and each needs its own spec +
merge gate in a FRESH session:
- **Cloud doc GENERATION** (cloud PDF + deep-dive) — a separate BACKEND slice (Supabase blob storage,
  durable serverless-safe jobs, deep-dive Gemini charging + guardrails). Its own full spec + dual-review.
- **Stage 3 (Sync)** — spans cloud+local (newer-wins); spec after the cloud app is feature-complete.
See [[frontend-subproject-design-state]].