# Adversarial Plan Review — Stage 3 Cloud Sync M2a (Claude, round 1)

Reviewed the full 14-task plan against the v10 spec and the real source it touches (`types/index.ts`, `lib/html-doc/model-store.ts` + `read-model.ts`, `lib/storage/metadata-store.ts`, `lib/storage/local/local-metadata-store.ts`, `lib/index-store.ts`, `lib/storage/supabase/supabase-metadata-store.ts`, `lib/storage/principal.ts`, `lib/pipeline.ts`, `lib/job-queue/producer.ts`, migrations `0007`/`0009`/`0016`, `app/api/videos/[id]/regenerate/route.ts`, `app/api/videos/[id]/archive/route.ts`, `scripts/check-service-confinement.ts`, `worker/main.ts`).

## BLOCKING

### B1 — Corrections-currency signal never stamped on the only path that applies corrections (Task 4)
The only path that applies corrections — `app/api/videos/[id]/regenerate/route.ts` — rewrites MD with `fs.writeFile` (68) and updates via `updateVideoFields(...,{corrections})` (55) and `{tldr,takeaways,summaryHtml:null}` (71). It never stamps `mdGeneratedAt`/`mdCorrectionsHash`. Task 4 only stamps at first-generation (`pipeline.ts:252-276`, corrections undefined → mdHash('')). Plan note line 677 hand-waves regenerate as "covered by persist_summary" — false; regenerate touches neither.
Failure: author fixes name via corrections; mdCorrectionsHash stays mdHash('') → corrections-stale forever → a stale higher-major uncorrected MD overwrites it. Exactly the §5.3 hazard.
Fix: stamp mdGeneratedAt + mdCorrectionsHash=mdHash(trimmedCorrections ?? '') on the regenerate write; test asserts post-regenerate record is corrections-current.

### B2 — Migration 0021 creates OVERLOADS not replacements; existing writes break (Task 3)
Adding `p_edited_at timestamptz default now()` with `create or replace` yields a NEW overload; old 4-arg/3-arg functions remain granted. `SupabaseMetadataStore.updateVideoAnnotations` calls with 4 keys (256) → both overloads match → PostgREST PGRST203 "could not choose the best candidate function". Manual Archive (archive/route.ts:85) and review route break. Same for merge_video_data (125). Plan's Task 3 tests pass only because they pass p_edited_at explicitly.
Fix: `drop function update_video_annotations(uuid,text,jsonb,text[]);` and `drop function merge_video_data(uuid,text,jsonb);` before creating new signatures.

## HIGH

### H1 — Task 12 leaves the most safety-critical core as a placeholder, no behaviors table, no adversarial review
Atomic Class-A transfer reduced to `// skeleton` (1680-1734). Per project Per-Task Checklist, this (async state machine, multiple error paths) REQUIRES an Enumerated Behaviors table + Codex review; has neither. Also asserts worker-only staged→promote plumbing (service-role) reusable from a user-session CLI without addressing RLS/grants under `authenticated`.
Fix: split into (a) union enumeration + orchestration, (b) atomic transfer/finalize under user session with behaviors table (stage-fail/promote-fail/finalize-fail/manifest-not-advanced), (c) companion + counters; run behaviors review on (b).

## MEDIUM
- M1 — 0021 persist_summary as shown DROPS the playlist-ownership guard (0009:109-110) despite the note saying "verbatim". Copy 0009 body verbatim + 2 keys only.
- M2 — check:confinement walks only app/pages/worker/middleware (63-72), NOT scripts/ or lib/cloud-sync/. The no-service-role assurance is vacuous. Add scripts/ to collectEntrypoints or an import-guard test for lib/cloud-sync/**.
- M3 — integration harness helpers (makeOwnerContext, seedLocalPlaylist, spendLedgerTotal, syncDeps({failCloudPromote}), readManifest, ...) are undesigned; no task builds them. Add explicit harness task before T12.
- M4 — Task 4 tests non-production local updateVideoAnnotations (local-metadata-store.ts:62-66 says shape-parity only); real local edits flow through updateVideoFields. Add unit test for updateVideoFields({corrections}) stamping and non-Class-B no-stamp.
- M5 — reconcileField logs spurious conflict when both sides same value, different timestamps (short-circuits only on value AND editedAt equal, 918). Fix: short-circuit on value equality alone, no conflict.

## LOW
- L1 — archived-only write creates empty annotationsEditedAt:{} (unconditional jsonb_set, 448-453); mirror merge_video_data's `when v_stamp <> '{}'` guard.
- L2 — one-sided hydrate returns needsRegen:false before corrections-currency check (1064-1070); hydrating a corrections-stale MD won't raise R8.
- L3 — conflict-log dedup key omits playlistKey (1304); same tuple in two playlists dedups to one.
- L4 — no test asserts additive-create excludes regenerable cache (summaryHtml/PDF) per §5.6.

## Correct (checked, not findings)
- Timestamp formats consistent (SQL to_char 3-digit-ms Z matches toISOString; offset value only used as provisional/backfilled, skip-guard prevents newer() reaching it).
- Dropping .strict() safe; new fields optional and flow through both readIndex impls. Money path clean (sync-run imports nothing from producer). SupabaseMetadataStore is a class taking a client. Class-A table matches §5.3 (9 rows); Class-B matches §5.4.

**Verdict: NOT CONVERGED** (2 Blocking, 1 High).
