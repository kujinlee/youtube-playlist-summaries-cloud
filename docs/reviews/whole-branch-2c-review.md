# Whole-Branch Dual Review — Stage 2c (Cloud Doc Consumption, Frontend)

**Branch:** feat/stage-2c-cloud-doc-consumption. **Diff:** merge-base(master,HEAD) `76e0590`..`3a0b102` (26 commits, 8 tasks). **Date:** 2026-07-11.
**Reviewers:** Codex (gpt-5.5) + Claude (opus, independent). **Gate:** final, before auto-merge.
**Verdict: CLEAN and mergeable — 0 Blocking, 0 High (both reviewers).**

## Cross-cutting spine — verified sound (both)
- **`promoted` readiness predicate coherent across all 3 enforcement points:** client gate `VideoMenu` (`video.summaryReady===true`, derived at supabase-metadata-store.ts:54), owner serve route `app/api/html/[id]/route.ts:57-58` (committed→503/!promoted→404), share-create RPC `0017` (`v_promoted is distinct from true`→404). A gated action can only fire when promoted; every server path serves exactly promoted. No ready-action-that-404s, no gated-action-that-fires-when-not-ready.
- **stripComputed write-safety complete:** strips BOTH updatedAt + summaryReady, guards upsertVideo/updateVideoFields/bulkUpdateVideoFields; derived boolean never round-trips into videos.data. merge_video_data unchanged (input pre-stripped).
- **Share surface / focus / re-entrancy:** ShareDialog has NO self focus-restore; VideoRow owns restore (menuTriggerRef in onClose) — no double/lost focus. inFlightRef set synchronously in both handlers, gates guardedClose (backdrop+Escape+✕) — double-click + dismissal-during-flight inert. Complete + consistent.
- **401→UnauthorizedError→/login uniform** across createShare/revokeShare/ShareDialog.
- **Cross-task types coherent:** CreateShareResult/ShareTtl (T4)→T5; summaryReady? (T2)→T6/T7; onShare? (T6)→T7 optional-guarded. No dead code.

## Global constraints — all satisfied (swept, both)
(a) local app untouched (0 files under components/local, app/api/ingest, local store, serveLocal; shared VideoMenu/VideoRow all cloudMode-gated; showShare never true locally); (b) session-client only, no service_role in lib/client/components/cloud/share route; (c) merge_video_data unchanged (only migration 0017); (d) share-serve never charges / no guardrail weakened — 0017 changes only the RPC return signature (adds id), summaryReady is read-only derived; (e) real tokens only. Migration 0017: only migration, grants restored, qualified RETURNING, no other RPC/table.

## Verification
Codex: tsc pass, focused 2c slice 32 + api/store 31 pass. (npm run build blocked only by sandbox Google-fonts network restriction — not a code/SSR error.) Controller: full unit 1989/1989, tsc 0, integration 334 pass/2 skip (T8).

## Deferred follow-ups (both reviewers: non-blocking)
1. **[Medium — SPEC-SANCTIONED, not a defect]** Repeated "Create link" mints a new live token and overwrites `share` state; the prior token stays live + un-revokable from the dialog. **Spec §1 explicitly accepts this** ("repeated Create calls mint multiple valid tokens; acceptable for 2c; bulk cleanup is the deferred share-management slice's job"). Deferred to the share-management slice.
2. **[Low]** ShareDialog reads `window.location.origin` above the `typeof document` guard — safe-by-construction today (`share` always null on server → ternary short-circuits); harden if a future change seeds initial non-null share.
3. **[Low]** Migration 0017 same-name DROP+CREATE deploy-skew window — documented in the plan's Task 1 deploy-ordering note (atomic deploy required); acceptable for coordinated single-app deploy.
4. **[Low — already accepted, plan L2]** revoke `{revoked:false}` (already-revoked/non-owned) surfaced as success — correct for 2c; owner-isolation covered by integration test.

## Bottom line
**CLEAN → auto-merge authorized (standing grant, this batch).** No Blocking/High; the one Medium is spec-sanctioned; three Lows are follow-ups.
