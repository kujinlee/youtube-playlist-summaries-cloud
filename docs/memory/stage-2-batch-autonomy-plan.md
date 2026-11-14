---
name: stage-2-batch-autonomy-plan
description: "FIRES-WHEN: citing Stage 2b/2c (PRs #12, #13), the 2026-07-11 batch auto-merge grant, or the deferred cloud doc-generation slice — both merged; the grant is SPENT"
metadata: 
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

**Current state:** the 2026-07-11 batch is COMPLETE and its auto-merge grant is **SPENT**.
- **Stage 2b (cloud ingest) merged** — PR #12, `76e0590`, 2026-07-11.
- **Stage 2c (cloud doc consumption: view HTML, download MD/HTML, share-link UI) merged** — PR #13, `db5cbfc`, 2026-07-11.
- The grant covered 2b/2c only and is not a precedent. Merging is now governed by the house rule **MERGE WHEN READY**
  (owner 2026-10-25, `docs/dev-process.md`; [[push-is-mine-merging-is-theirs]]).
- **Stage 3 (Sync)** later merged on its own gate — PR #23, see [[stage3-cloud-sync-branch-state]].
- **Cloud doc GENERATION (cloud PDF + deep-dive)** was split out as a separate BACKEND slice (blob storage, durable
  serverless-safe jobs, Gemini charging + guardrails) needing its own spec + dual review; its status after 2026-07-11
  is not tracked here — check `docs/roadmap-to-launch.md`.

**Lessons worth keeping:**
- **Fresh context per slice.** Spec several slices in one sitting, but implement each in its own fresh session
  (plan + impl for several slices in one context risks fill-up and cross-slice bleed). Durable handoff = committed
  spec + plan + SDD ledger + git + memory.
- **Adversarial second-model review was load-bearing.** 2b: 6 real Highs the implementation and the Claude approval
  pass missed (T1 2× abort-contract races; T2 null-body TypeError + a Retry-After regression the fix introduced; T6
  double-submit spend re-entrancy; T7 fireIfAdvanced firing on regressions; T9 retained playlistUrl → wrong-playlist
  Refresh), plus a whole-branch **Blocking** no per-task review could see — Refresh was a 2nd createIngest spend path
  without the modal's synchronous mutex (fix `bb13c84`). On 5 of these Claude approved and Codex found the defect.
  2c: Codex again caught structural defects the Claude pass approved (T5 guardedClose gated on state not inFlightRef;
  T7 ShareDialog invalid DOM nesting under `<tbody>`, needed a portal). See [[dual-review-what-it-catches]].

**Deferred follow-ups (non-blocking):** 2b — abortableSleep clearTimeout (browser no-op); banner role=status/aria-live;
onProgress-aborts-signal edge; display-only stale-list/sort races. 2c — repeated "Create link" mints multiple live
tokens (spec §1-sanctioned); ShareDialog reads `window.location.origin` above the SSR guard; 0017 same-name DROP+CREATE
deploy-skew; revoke `{revoked:false}`-as-success.

## History
- Decided 2026-07-11 by the user at the 2b spec-approval gate. RESLICE after 2c exploration: the original "2c doc
  lifecycle" was not a clean frontend slice (cloud PDF + deep-dive generation were local-only), so 2c became
  consumption-only (absorbing the old "2d share+downloads") and generation was deferred.
- 2b plan converged at v5 `eef22a7` after 4 dual rounds (R1 3 Blocking + 5 High; R2 1 Blocking + 3 High). Final: tsc 0,
  unit 1955/1955, integration 331 pass/2 skip. Reviews `docs/reviews/task-2b-*.md`, `whole-branch-2b-review.md`.
- 2c: Post-Plan Gate 3 rounds; 8 tasks; whole-branch clean both halves. Final: tsc 0, unit 1989/1989, integration 334
  pass/2 skip. Reviews `docs/reviews/task-2c-*`, `whole-branch-2c-{codex,review}.md`.
- The grant required `--repo kujinlee/youtube-playlist-summaries-cloud` ([[gh-two-remotes-footgun]]). Push notifications
  need Remote Control paired and the user away from the terminal. See [[frontend-subproject-design-state]].
